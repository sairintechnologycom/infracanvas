class Infracanvas < Formula
  include Language::Python::Virtualenv

  desc "Interactive Terraform architecture diagrams with security scoring"
  homepage "https://infracanvas.dev"
  url "https://files.pythonhosted.org/packages/source/i/infracanvas/infracanvas-VERSION.tar.gz"
  sha256 "SHA256_PLACEHOLDER"
  license "MIT"

  depends_on "python@3.12"

  def install
    virtualenv_install_with_resources
  end

  test do
    assert_match "Usage", shell_output("#{bin}/infracanvas --help")
  end
end
