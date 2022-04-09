src = $(wildcard *.cpp)
bin = rage_mp3_reader
flags = -l:libmad.a -std=c++17 -static

$(bin): $(src)
	g++ $(src) $(flags) -o $(bin)

.PHONY: clean

clean:
	rm $(bin)