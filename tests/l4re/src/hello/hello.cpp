#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>

int main()
{
  std::string msg = "Hello from C++";

  std::thread t([&msg] { msg += " with threads"; });
  t.join();

  try
    {
      throw std::runtime_error(" and exceptions");
    }
  catch (std::exception const &e)
    {
      msg += e.what();
    }

  std::cout << msg << "!" << std::endl;
  return 0;
}
