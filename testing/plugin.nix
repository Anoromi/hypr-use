let
  pkgs = import /nix/store/c60zr86cdk6xm190q1h1iq06n45m3p8n-0zfsjx62jhgjl5xpsrqalcarxq1ik1b2-source { system = "x86_64-linux"; };
in pkgs.hyprlandPlugins.mkHyprlandPlugin {
  pluginName = "hypr-agent-portal";
  version = "0.4.0-local-0.55.4";
  meta = { description = "Local Portal test"; };
  src = ../vendor/hypr-agent-portal;
  nativeBuildInputs = pkgs.hyprland.nativeBuildInputs ++ [ pkgs.python3 ];
  buildInputs = pkgs.hyprland.buildInputs ++ [ pkgs.lua pkgs.nlohmann_json ];
  cmakeFlags = [ "-DBUILD_TESTING=ON" ];
}
