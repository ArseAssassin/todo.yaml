{
  description = "todo.yaml CLI shell";

  inputs = {
    nixpkgs.url = "nixpkgs/nixos-23.11";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem
      (system:
        let
          pkgs = import nixpkgs {
            inherit system;
          };
        in
        with pkgs;
        {
          devShells.default = mkShell {
            packages = with python311Packages; [
              python311
              pylint
              click
              jq
              ruyaml
              setuptools
              colorama
            ];
          };
        }
      );
}