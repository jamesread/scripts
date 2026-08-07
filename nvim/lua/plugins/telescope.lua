return {
  "nvim-telescope/telescope.nvim",
  tag = "0.1.8",
  dependencies = {
    "nvim-lua/plenary.nvim",
    "nvim-telescope/telescope-ui-select.nvim",
  },
  config = function()
    local sorters = require("telescope.sorters")

    require("telescope").setup({
      defaults = {
        sorting_strategy = "ascending",
        mappings = {
          i = {
            ["<C-T>"] = "which_key",
          },
        },
      },
      pickers = {
        lsp_document_symbols = {
          sorter = sorters.get_generic_fuzzy_sorter(),
          sorting_strategy = "ascending",
        },
      },
      extensions = {
        ["ui-select"] = require("telescope.themes").get_dropdown({}),
      },
    })

    require("telescope").load_extension("ui-select")
  end,
}
