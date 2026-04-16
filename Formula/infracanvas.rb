class Infracanvas < Formula
  desc "Scan Terraform code and generate annotated infrastructure diagrams with security scores"
  homepage "https://infracanvas.dev"
  url "https://github.com/infracanvas/infracanvas/archive/refs/tags/v0.1.0.tar.gz"
  # sha256 will be filled at release time after tarball is published
  sha256 "FILL_AFTER_RELEASE"
  license "MIT"

  depends_on "python@3.12"
  depends_on "node" => :build

  def install
    cd "viewer" do
      system "npm", "ci"
      system "npm", "run", "build"
      mkdir_p buildpath/"cli/infracanvas/export"
      cp "dist/index.html", buildpath/"cli/infracanvas/export/viewer_template.html"
    end
    cd "cli" do
      virtualenv_install_with_resources
    end
  end

  test do
    system bin/"infracanvas", "--version"
  end
end
