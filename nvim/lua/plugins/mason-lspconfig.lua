return {
  "williamboman/mason-lspconfig.nvim",
  dependencies = {
    "williamboman/mason.nvim",
    "neovim/nvim-lspconfig",
    "hrsh7th/nvim-cmp", -- set cmp LSP capabilities before servers enable
  },
  opts = {
    -- Installed Mason LSP servers are auto-enabled via vim.lsp.enable().
    ensure_installed = { "gopls" },
  },
}
