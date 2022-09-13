#include <holler.h>
#include "greet.h"

void greet(const char *name)
{
   holler("Hi ");
   holler(name);
   holler("! How are you doing?\n");
}
