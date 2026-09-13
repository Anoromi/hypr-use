{ pkgs }:
pkgs.runCommand "hypr-use-test-seat" {
 nativeBuildInputs = [ pkgs.stdenv.cc pkgs.pkg-config pkgs.wayland-scanner ];
 buildInputs = [ pkgs.wayland pkgs.libxkbcommon ];
} ''
 wayland-scanner client-header ${./protocols/virtual-keyboard-unstable-v1.xml} keyboard.h
 wayland-scanner private-code ${./protocols/virtual-keyboard-unstable-v1.xml} keyboard.c
 wayland-scanner client-header ${./protocols/wlr-virtual-pointer-unstable-v1.xml} pointer.h
 wayland-scanner private-code ${./protocols/wlr-virtual-pointer-unstable-v1.xml} pointer.c
 mkdir -p $out/bin
 cc -I. ${./test-seat.c} keyboard.c pointer.c $(pkg-config --cflags --libs wayland-client xkbcommon) -o $out/bin/hypr-use-test-seat
''
