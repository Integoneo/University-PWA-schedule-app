.PHONY: all run clean

all:
	cmake -S . -B build
	make -C build

run: all
	make -C build run

clean:
	rm -rf build/*
