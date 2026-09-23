let
  pkgs = import <nixpkgs> {};
in pkgs.mkShell {
  packages = [ (pkgs.python3.withPackages (p: [ p.pygobject3 ])) pkgs.gtk4 pkgs.ffmpeg ];
}
