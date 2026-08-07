return {
  "williamboman/mason-lspconfig.nvim",
  dependencies = {
    "williamboman/mason.nvim",
    "neovim/nvim-lspconfig",
    "hrsh7th/cmp-nvim-lsp",
  },
  opts = {},
  config = function(_, opts)
    vim.lsp.config("*", {
      capabilities = require("cmp_nvim_lsp").default_capabilities(),
    })
    require("mason-lspconfig").setup(opts)
  end,
}
