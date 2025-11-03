/*
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
#ifndef LIST_H
#define LIST_H

#include <inttypes.h>
#include <stddef.h>

struct list_node
{
	struct list_node *prev;
	struct list_node *next;
};

#define LIST_HEAD(type__, anchor__) \
	struct { \
		struct list_node head; \
		type__ typevar[0]; \
		struct { \
			char off[offsetof(type__, anchor__)]; \
		} offsetvar[0]; \
	}

#define DEFINE_LIST_HEAD(name, type, anchor) \
	LIST_HEAD(type, anchor) name = { { &(name).head, &(name).head } }


static inline void list_node_init(struct list_node *n)
{
	n->next = n->prev = n;
}

static inline void list_node_append(struct list_node *l, struct list_node *e)
{
	e->next = l->next;
	e->prev = l;
	l->next->prev = e;
	l->next = e;
}

static inline void list_node_prepend(struct list_node *l, struct list_node *e)
{
	e->next = l;
	e->prev = l->prev;
	l->prev->next = e;
	l->prev = e;
}

static inline void list_node_del(struct list_node *e)
{
	e->prev->next = e->next;
	e->next->prev = e->prev;
	e->next = e->prev = e;
}

static inline int list_node_in_list(struct list_node *e)
{
	return e->next != e;
}


#define list_init(l) \
	do { \
		(l)->head.prev = (struct list_node *)(l); \
		(l)->head.next = (struct list_node *)(l); \
	} while (0)

#define list_empty(l) \
	((l).head.next == &(l).head)

#define list_add_front(head__, elem__) \
	do { \
		list_node_append(&((head__)->head), (struct list_node *)((uintptr_t)(elem__) + sizeof((head__)->offsetvar[0].off))); \
	} while (0)

#define list_add_tail(head__, elem__) \
	do { \
		list_node_prepend(&((head__)->head), (struct list_node *)((uintptr_t)(elem__) + sizeof((head__)->offsetvar[0].off))); \
	} while (0)

#define list_element_type(head__) \
	typeof((head__).typevar[0])*

#define list_front(head__) \
	((list_element_type((head__)))((uintptr_t)(head__).head.next - sizeof((head__).offsetvar[0].off)))

#define list_pop_front(head__) \
	({ \
		list_element_type(*head__) n = list_front(*head__); \
		list_node_del((head__)->head.next); \
		n; \
	})


#define list_for_each(head__, var__) \
	for (typeof((head__).typevar[0]) *var__ = (void*)((uintptr_t)(head__).head.next - sizeof((head__).offsetvar[0].off)); \
	     ((uintptr_t)var__ + sizeof((head__).offsetvar[0].off)) != (uintptr_t)&(head__).head; \
	     var__ = (typeof((head__).typevar[0]) *)((uintptr_t)((struct list_node *)((uintptr_t)var__ + sizeof((head__).offsetvar[0].off)))->next - sizeof((head__).offsetvar[0].off)))

#define list_iterate(head__, var__) \
	for (; \
	     ((uintptr_t)var__ + sizeof((head__).offsetvar[0].off)) != (uintptr_t)&(head__).head; \
	     var__ = (typeof((head__).typevar[0]) *)((uintptr_t)((struct list_node *)((uintptr_t)var__ + sizeof((head__).offsetvar[0].off)))->next - sizeof((head__).offsetvar[0].off)))

#define list_for_each_safe(head__, var__) \
	for (typeof((head__).typevar[0]) *var__ = (void*)((uintptr_t)(head__).head.next - sizeof((head__).offsetvar[0].off)), *var__##_next; \
	     (((uintptr_t)var__ + sizeof((head__).offsetvar[0].off)) != (uintptr_t)&(head__).head) && (var__##_next = (typeof((head__).typevar[0]) *)((uintptr_t)((struct list_node *)((uintptr_t)var__ + sizeof((head__).offsetvar[0].off)))->next - sizeof((head__).offsetvar[0].off)), 1); \
	     var__ = var__##_next)


static inline void list_head_move__(struct list_node *dst, struct list_node *src)
{
	src->prev->next = dst;
	src->next->prev = dst->prev;
	dst->prev->next = src->next;
	dst->prev = src->prev;

	list_node_init(src);
}

#define list_move_tail(dst_head__, src_head__) \
	do { \
		if (!list_empty(src_head__)) \
			list_head_move__(&(dst_head__).head, &(src_head__).head); \
	} while (0)

#endif
