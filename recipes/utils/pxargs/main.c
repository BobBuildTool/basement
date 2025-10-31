/*
 * Small xargs like program that takes part of the make jobserver.
 *
 * Attention: assumes zero terminated input strings (-print0)!
 *
 * Copyright (c) 2025 Jan Klötzke <jan@kloetzke.net>
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

#define _GNU_SOURCE

#include <assert.h>
#include <ctype.h>
#include <errno.h>
#include <fcntl.h>
#include <getopt.h>
#include <limits.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#include "list.h"

#define EXIT_ERROR (EXIT_FAILURE + 1)

// Artificial token that represents our implicit token that we already have.
#define MY_TOKEN 0x100

struct input_file {
	struct list_node node;
	char *name;
	dev_t dev;
	ino_t ino;
};

struct running_child {
	pid_t pid;
	struct input_file *f;
	int token;
};

int input_fd = 0;
char input_buf[PATH_MAX];
unsigned input_len;

DEFINE_LIST_HEAD(input_files, struct input_file, node);

int jobs_pipe_rd = -1, jobs_pipe_wr = -1;
int my_token = MY_TOKEN;

int jobs_argc;
char **jobs_argv;
int jobs_running, jobs_possible;

volatile sig_atomic_t exit_status;
volatile sig_atomic_t zombies;

struct running_child *children;

char need_input, need_tokens;

/**
 * Signal termination.
 *
 * Will signal that we want to terminate. Errors take precedence above clean
 * termination.
 */
static void set_done(int result)
{
	assert(result > 0);
	if (exit_status < result)
		exit_status = result;
}

static int is_done(void)
{
	// We need to wait until the last child was reaped.
	if (jobs_running)
		return 0;

	if (exit_status)
		// Premature termination
		return exit_status;
	else
		// Regular termination if pipeline is idle
		return input_fd < 0 && list_empty(input_files) && !jobs_running;
}


static struct input_file *new_input_file(char *fn)
{
	struct input_file *ret = calloc(1, sizeof(struct input_file));
	list_node_init(&ret->node);
	ret->name = strdup(fn);

	struct stat sb;
	if (lstat(fn,  &sb) == 0) {
		ret->dev = sb.st_dev;
		ret->ino = sb.st_ino;
	} else
		perror(fn);

	return ret;
}

static void delete_input_file(struct input_file *f)
{
	assert(!list_node_in_list(&f->node));
	free(f->name);
	free(f);
}


static int get_next_token(void)
{
	// Always use our implicit job token first!
	if (my_token) {
		my_token = 0;
		return MY_TOKEN;
	}

	char buf;
	switch (read(jobs_pipe_rd, &buf, 1)) {
		case 1:
			return buf;
		case 0:
			// That should not happen. The jobs token pipe was
			// closed on the write end!
			fprintf(stderr, "Broken jobs pipe");
			set_done(EXIT_ERROR);
			return -1;
		case -1:
			if (errno == EINTR || errno == EAGAIN || errno == EWOULDBLOCK)
				return -1;
			perror("jobs pipe read");
			set_done(EXIT_ERROR);
			return -1;
	}

	// unreachable
	abort();
}

void return_token(int token)
{
	if (token == MY_TOKEN) {
		my_token = MY_TOKEN;
	} else {
		char buf = token;
		for (;;) {
			ssize_t r = write(jobs_pipe_wr, &buf, 1);
			if (r > 0) {
				break;
			} else if (r == 0) {
				fprintf(stderr, "Broken jobs pipe");
				set_done(EXIT_ERROR);
			} else if (r < 0 && errno != EINTR) {
				perror("jobs pipe write");
				set_done(EXIT_ERROR);
			}
		}
	}
}


static void add_child(pid_t pid, struct input_file *f, int token)
{
	// We know that there is enough room in the array
	struct running_child *c = children;
	while (c->pid)
		++c;

	c->pid = pid;
	c->f = f;
	c->token = token;
}

static void remove_child(pid_t pid)
{
	struct running_child *c = children;
	while (c->pid != pid)
		++c;

	c->pid = 0;
	return_token(c->token);
	delete_input_file(c->f);
}

static int can_use_file(struct input_file *f)
{
	// Just in case the file couldn't be read...
	if (f->dev == 0 && f->ino == 0)
		return 1;

	for (int i = 0; i < jobs_possible; i++) {
		if (children[i].pid == 0)
			continue;

		// If a child is running that procsses the same file
		// (hardlink), we postpone it.
		if (children[i].f->dev == f->dev && children[i].f->ino == f->ino)
			return 0;
	}

	return 1;
}


static struct input_file *read_next_files()
{
	// Nothing to do if input is already exhausted or we're going down.
	if (input_fd < 0 || exit_status)
		return NULL;

	// We must not call read() with a length of zero. The post-read logic
	// ensures that there is still room in the buffer.
	ssize_t r = read(input_fd, &input_buf[input_len], sizeof(input_buf) - input_len);
	if (r < 0) {
		if (errno == EAGAIN || errno == EWOULDBLOCK)
			return NULL;
		if (errno == EINTR)
			return NULL;

		perror("stdin read");
		set_done(EXIT_ERROR);
		return NULL;
	} else if (r == 0) {
		// End of input stream.
		input_fd = -1;
		return NULL;
	} else
		input_len += (unsigned)r;

	// Dissect input stream into individual files.
	struct input_file *ret = NULL;
	char *next = input_buf, *end;
	unsigned len = input_len;
	while (len && (end = (char *)memchr(next, 0, len))) {
		struct input_file *nf = new_input_file(next);
		list_add_tail(&input_files, nf);

		if (!ret)
			ret = nf;

		len -= (end - next) + 1;
		next = end + 1;
	}

	// If the whole buffer was filled without a single, full file name,
	// we're screwed.
	if (len >= sizeof(input_buf)) {
		fprintf(stderr, "Maximum path length reached!\n");
		set_done(EXIT_ERROR);
		return NULL;
	}

	input_len = len;
	if (next != input_buf && len)
		memmove(input_buf, next, len);

	return ret;
}

/**
 * Get next file from stdin.
 *
 * This will check for potential hard links of files that are already processed
 * by a child.
 */
static struct input_file *get_next_file(void)
{
	// First let's see if any of the already ingested files can be used.
	list_for_each(input_files, n) {
		if (can_use_file(n)) {
			list_node_del(&n->node);
			return n;
		}
	}

	// Either we have no files or they were not usable. Read the next chunk
	// of files...
	struct input_file *n = read_next_files();
	if (!n)
		return NULL;

	// Starting from the first read file name, try to find one that is
	// usable...
	list_iterate(input_files, n) {
		if (can_use_file(n)) {
			list_node_del(&n->node);
			return n;
		}
	}

	return NULL;
}

static void unget_next_file(struct input_file *f)
{
	list_add_front(&input_files, f);
}

static void process_file(char *fn)
{
	jobs_argv[jobs_argc - 1] = fn;
	execvp(jobs_argv[0], jobs_argv);

	perror("execve");
	fprintf(stderr, "Could not process %s\n", fn);
	exit(EXIT_FAILURE);
}

static pid_t fork_file_worker(char *fn)
{
	pid_t child_pid = fork();
	if (child_pid == 0)
		process_file(fn);
	else if (child_pid < 0)
		perror("fork");

	return child_pid;
}


static unsigned schedule(void)
{
	unsigned scheduled = 0;

	while (jobs_running < jobs_possible && !exit_status) {
		struct input_file *next = get_next_file();
		if (!next) {
			need_input = 1;
			break;
		}

		int token = get_next_token();
		if (token < 0) {
			unget_next_file(next);
			need_tokens = 1;
			break;
		}

		pid_t child = fork_file_worker(next->name);
		if (child > 0) {
			add_child(child, next, token);
			jobs_running++;
		} else {
			set_done(EXIT_ERROR);
			return_token(token);
			delete_input_file(next);
			break;
		}

		scheduled++;
	}

	return scheduled;
}

static void wait_event(void)
{
	fd_set rfds;

	if (is_done())
		return;

	// Block SIGCHLD before going to sleep. We only want the handler to
	// fire during pselect() after we checked! This is needed so that the
	// waiting does not race with a concurrent SIGCHLD.
	sigset_t block_set, orig_set;
	sigemptyset(&block_set);
	sigaddset(&block_set, SIGCHLD);
	if (sigprocmask(SIG_BLOCK, &block_set, &orig_set) < 0) {
		perror("sigprocmask");
		return;
	}

	if (zombies) {
		// The SIGCHLD just arrived. Don't sleep.
	} else if (!exit_status) {
		FD_ZERO(&rfds);
		int nfds = 0;
		if (need_input && input_fd >= 0) {
			FD_SET(0, &rfds);
			nfds++;
		}
		if (need_tokens) {
			FD_SET(jobs_pipe_rd, &rfds);
			nfds++;
		}
		pselect(nfds, &rfds, NULL, NULL, NULL, &orig_set);
		need_input = need_tokens = 0;
	} else if (jobs_running > 0) {
		pselect(0, NULL, NULL, NULL, NULL, &orig_set);
	}

	sigprocmask(SIG_SETMASK, &orig_set, NULL);
}

static int reap_childs(void)
{
	int reaped = 0;
	int status;

	zombies = 0;

	while (jobs_running > 0) {
		pid_t pid = waitpid(-1, &status, WNOHANG);
		if (pid > 0) {
			reaped++;
			jobs_running--;
			remove_child(pid);
			if (WIFEXITED(status)) {
				if (WEXITSTATUS(status) != 0)
					set_done(EXIT_FAILURE);
			} else if (WIFSIGNALED(status)) {
				set_done(EXIT_FAILURE);
			} else {
				fprintf(stderr, "unexpected waitpid status %d", status);
				set_done(EXIT_ERROR);
			}
		} else if (pid == 0) {
			break;
		} else if (errno != EINTR) {
			perror("waitpid");
			set_done(EXIT_ERROR);
			break;
		}
	}

	return reaped;
}

static void handle_sigchld(int signo)
{
	(void)signo;
	zombies = 1;
}

static void handle_sigint(int signo)
{
	(void)signo;
	set_done(EXIT_FAILURE);
}

static int handle_signal(int signo, void (*handler)(int))
{
	struct sigaction act = { 0 };
	act.sa_handler = handler;
	if (sigaction(signo, &act, NULL) < 0) {
		perror("sigaction");
		return 0;
	}

	return 1;
}

static void parse_jobs_auth_named(char *path)
{
	jobs_pipe_rd = open(path, O_RDONLY | O_CLOEXEC | O_NONBLOCK);
	if (jobs_pipe_rd < 0) {
		perror(path);
		return;
	}

	jobs_pipe_wr = open(path, O_WRONLY | O_CLOEXEC);
	if (jobs_pipe_wr < 0) {
		perror(path);
		close(jobs_pipe_rd);
		jobs_pipe_rd = -1;
		return;
	}
}

static void parse_jobs_auth_anon(char *numbers)
{
	char *end;

	errno = 0;
	jobs_pipe_rd = strtol(numbers, &end, 0);
	if (end == numbers || errno || jobs_pipe_rd < 0 || *end != ',') {
		jobs_pipe_rd = jobs_pipe_wr = -1;
		return;
	}

	numbers = end + 1;
	jobs_pipe_wr = strtol(numbers, &end, 0);
	if (end == numbers || errno || jobs_pipe_wr < 0 || *end != '\0') {
		jobs_pipe_rd = jobs_pipe_wr = -1;
		return;
	}
}

// See https://www.gnu.org/software/make/manual/html_node/POSIX-Jobserver.html
static void parse_jobs_auth(char *arg)
{
	if (strncmp(arg, "fifo:", 5) == 0)
		parse_jobs_auth_named(arg + 5);
	else
		parse_jobs_auth_anon(arg);
}

#define OPT_JOBSERVER_AUTH	0x100

static int parse_options(int argc, char **argv, int from_cmd_line)
{
	optind = 1;

	static struct option long_options[] = {
		{"jobserver-auth", required_argument, NULL, OPT_JOBSERVER_AUTH},
		{0, 0, 0, 0}
	};

	for (;;) {
		int c = getopt_long(argc, argv, "j:", long_options, NULL);
		if (c == -1)
			break;

		switch (c) {
			case 'j':
				if (jobs_possible && from_cmd_line) {
					fprintf(stderr, "Warning: override inherited job server!\n");
					if (jobs_pipe_rd >= 0)
						close(jobs_pipe_rd);
					if (jobs_pipe_wr >= 0)
						close(jobs_pipe_wr);
					jobs_pipe_rd = jobs_pipe_wr = -1;
					unsetenv("MAKEFLAGS");
				}
				jobs_possible = atoi(optarg);
				break;
			case OPT_JOBSERVER_AUTH:
				if (!from_cmd_line) {
					parse_jobs_auth(optarg);
					break;
				}
				// fallthrough
			case '?':
				if (from_cmd_line) {
					fprintf(stderr, "Unknown argument: %s", argv[optind]);
					exit(EXIT_FAILURE);
				}
				break;
			default:
				abort();
		}
	}

	return optind;
}

static void parse_makeflags(char const *mf)
{
	size_t len = strlen(mf);
	if (len == 0)
		return;

	char *args = NULL;

	// If MAKEFLAGS starts with a space, there are no single letter
	// options. Otherwise, we have to add a "-"...
	if (isblank((unsigned char)*mf)) {
		while (*mf && isblank((unsigned char)*mf))
			++mf;

		if (!*mf)
			return;

		args = strdup(mf);
	} else {
		// We need to add a "-" for single letter options.
		args = malloc(len + 2);
		args[0] = '-';
		strcpy(&args[1], mf);
	}

	// The worst case are single letters with spaces in between. We need an
	// additional argv[0] and a trailing NULL pointer.
	char **argv = malloc(((len + 2) / 2 + 2) * sizeof(char *));
	argv[0] = ""; // dummy because getopt always starts at optind == 1
	int argc = 1;

	// Assume words separated by whitespace. There doesn't seem to be a
	// formal definition for how whitespace in option arguments should be
	// handled.
	char *arg = args;
	while (*arg) {
		argv[argc++] = arg;
		while (*arg && !isblank((unsigned char)*arg))
			++arg;
		if (!*arg)
			break;

		*arg++ = '\0';

		while (*arg && isblank((unsigned char)*arg))
			++arg;
	}
	argv[argc] = NULL;

	parse_options(argc, argv, 0);

	free(argv);
	free(args);
}

int main(int argc, char **argv)
{
	// Parse make jobserver configuration.
	char const *mf = getenv("MAKEFLAGS");
	if (mf)
		parse_makeflags(mf);

	// Make is weird when it doesn't think the rule is a recursive "make".
	// It will still pass the parallel make information but set the job
	// token pipe file descriptors to a negative number.
	if (jobs_possible > 1 && (jobs_pipe_rd < 0 || jobs_pipe_wr < 0)) {
		fprintf(stderr, "Missing job server in recursive make! Add '+' to your Makefile rule.\n");
		jobs_possible = 0;
	}

	// Parse command line options.
	int used_args = parse_options(argc, argv, 1);

	jobs_argc = argc - used_args + 1;
	if (jobs_argc < 1) {
		fprintf(stderr, "usage: %s [-j N] [--] command [intial-args...]\n",
		        basename(argv[0]));
		return 1;
	}

	// Prepare argv[] of children
	jobs_argv = malloc(sizeof(char *) * (jobs_argc + 1));
	for (int i = 0; i < jobs_argc - 1; i++)
		jobs_argv[i] = argv[used_args + i];
	jobs_argv[jobs_argc] = NULL;

	// Make sure the job server is in the right state
	if (jobs_possible <= 0)
		jobs_possible = 1;

	// Create our own jobserver if we're not running under one already.
	if (jobs_possible > 1 && (jobs_pipe_rd < 0 || jobs_pipe_wr < 0)) {
		int pipefd[2];
		if (pipe(pipefd) < 0) {
			perror("pipe2");
			return EXIT_FAILURE;
		}
		jobs_pipe_rd = pipefd[0];
		jobs_pipe_wr = pipefd[1];

		for (int i = 0; i < jobs_possible - 1; i++)
			write(jobs_pipe_wr, "a", 1);

		// The first whitespace in MAKEFLAGS is important! It means
		// there are no single letter options.
		char buf[64];
		int len = snprintf(buf, sizeof(buf), " -j%d --jobserver-auth=%d,%d",
		                   jobs_possible, jobs_pipe_rd, jobs_pipe_wr);
		if (len < 0 || (unsigned)len >= sizeof(buf)) {
			fprintf(stderr, "Could not synthesize MAKEFLAGS\n");
			return EXIT_ERROR;
		}
		setenv("MAKEFLAGS", buf, 1);
	}

	children = calloc(jobs_possible, sizeof(*children));

	// Establish SIGCHLD handler. It will wake us from any blocking operation.
	struct sigaction act = { 0 };
	act.sa_handler = &handle_sigchld;
	act.sa_flags = SA_NOCLDSTOP;
	if (sigaction(SIGCHLD, &act, NULL) < 0) {
		perror("sigaction");
		return 2;
	}

	// Catch SIGINT/SIGTERM/... to shut down cleanly on interruption.
	if (!handle_signal(SIGINT, &handle_sigint))
		return EXIT_ERROR;
	if (!handle_signal(SIGTERM, &handle_sigint))
		return EXIT_ERROR;
	if (!handle_signal(SIGALRM, &handle_sigint))
		return EXIT_ERROR;
	if (!handle_signal(SIGHUP, &handle_sigint))
		return EXIT_ERROR;
	if (!handle_signal(SIGQUIT, &handle_sigint))
		return EXIT_ERROR;

	// Catch SIGPIPE as well, just in case we're part of a pipeline.
	if (!handle_signal(SIGPIPE, &handle_sigint))
		return EXIT_ERROR;

	// Run as long as no error was encountered or if there is some
	// subprocess running...
	while (!is_done()) {
		if (!reap_childs() && !schedule())
			wait_event();
	}

	return exit_status;
}
