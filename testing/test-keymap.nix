let pkgs = import /nix/store/imqw0rclpcn2r5r86v32n8w7zbd4anma-ysl3pgmc60y42ylza8kyyk1g0pzgj4qj-source { system = "x86_64-linux"; };
in pkgs.runCommand "hypr-use-keymap-tests" {
 nativeBuildInputs = [pkgs.stdenv.cc pkgs.pkg-config];
 buildInputs = [pkgs.libxkbcommon];
} ''
 c++ -std=c++23 -I${../vendor/hypr-agent-portal-0.56.2/src/plugin} ${./test-keymap.cpp} $(pkg-config --cflags --libs xkbcommon) -o test
 ./test > $out
''
