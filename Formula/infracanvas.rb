class Infracanvas < Formula
  desc "Interactive Terraform architecture diagrams with security findings and cost estimates"
  homepage "https://infracanvas.dev"
  url "https://github.com/infracanvas/infracanvas/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "FILL_AFTER_RELEASE"
  license "MIT"

  depends_on "python@3.12"

  def install
    system "pip3", "install", "--prefix=#{prefix}", "infracanvas==0.1.0"
  end

  test do
    system "#{bin}/infracanvas", "--version"
  end
end
