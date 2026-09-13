let
  pkgs = import /nix/store/imqw0rclpcn2r5r86v32n8w7zbd4anma-ysl3pgmc60y42ylza8kyyk1g0pzgj4qj-source { system = "x86_64-linux"; };
in pkgs.hyprlandPlugins.mkHyprlandPlugin {
  pluginName = "hypr-agent-portal";
  version = "0.4.0-local-0.56.2";
  meta = { description = "Local Portal test"; };
  src = ../vendor/hypr-agent-portal-0.56.2;
  nativeBuildInputs = pkgs.hyprland.nativeBuildInputs ++ [ pkgs.python3 ];
  buildInputs = pkgs.hyprland.buildInputs ++ [ pkgs.lua pkgs.nlohmann_json ];
  cmakeFlags = [ "-DBUILD_TESTING=ON" ];
}
