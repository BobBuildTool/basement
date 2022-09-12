#include <greet.h>
#include <stdio.h>

int main(int argc, char **argv)
{
	if (argc < 2) {
		fprintf(stderr, "Pass your name as argument...\n");
		return 1;
	}

	greet(argv[1]);
	return 0;
}
