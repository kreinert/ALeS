CXX = c++
CXXFLAGS = -std=gnu++0x -Wall -O2

# OpenMP: Homebrew libomp on macOS, or system -fopenmp elsewhere
UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
  ifeq ($(shell test -d /opt/homebrew/opt/libomp && echo yes),yes)
    OMPFLAGS = -Xpreprocessor -fopenmp -I/opt/homebrew/opt/libomp/include -L/opt/homebrew/opt/libomp/lib -lomp
  else ifeq ($(shell test -d /usr/local/opt/libomp && echo yes),yes)
    OMPFLAGS = -Xpreprocessor -fopenmp -I/usr/local/opt/libomp/include -L/usr/local/opt/libomp/lib -lomp
  else
    OMPFLAGS =
  endif
else
  OMPFLAGS = -fopenmp
endif

ALeSc : ALeSc.cpp
	$(CXX) $(CXXFLAGS) $(OMPFLAGS) ALeSc.cpp -o ALeSc

ALeS : ALeS.cpp
	g++ -std=gnu++0x -Wall ALeS.cpp -o ALeS

clean :
	rm -f ALeS ALeSc
