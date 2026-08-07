return {
  "nvim-treesitter/nvim-treesitter",
  build = ":TSUpdate",
  main = "nvim-treesitter.configs",
  opts = {
    highlight = { enable = true },
    auto_install = true,
    ensure_installed = {
      "lua",
      "go",
      "yaml",
      "html",
      "javascript",
      "vim",
      "vimdoc",
      "query",
    },
  },
}
