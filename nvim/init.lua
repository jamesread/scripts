vim.o.number = true
vim.o.relativenumber = true
vim.o.termguicolors = false
vim.o.tabstop = 4
vim.o.softtabstop = 4
vim.o.shiftwidth = 4

require("config.lazy")

vim.keymap.set("n", "<S-R>", ":Neotree action=focus reveal=true<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "<C-P>", ":bp<cr>", { noremap = true, silent = true})
vim.keymap.set("n", "<C-N>", ":bn<cr>", { noremap = true, silent = true})
vim.keymap.set("n", "<C-T>", ":Telescope lsp_document_symbols<cr>", { noremap = true, silent = true})
vim.keymap.set("n", "<C-F>", ":Telescope find_files<cr>", { noremap = true, silent = true})
vim.api.nvim_set_keymap("n", "<S-K>", "i[text](url)<Esc>2hi", { noremap = true, silent = true })
vim.api.nvim_set_keymap("v", "<leader>k", '"sy<ESC>`<v`>s[<C-r>s](url)<Left>', { noremap = true, silent = true })

vim.cmd.set("background=light")
vim.cmd.colorscheme("vim")

require("lualine").setup{
	options = {
		icons_enabled = true,
		theme = 'nord',
	}
}
require("mason").setup({})
require("mason-lspconfig").setup({
  handlers = {
    function(server_name)
      require('lspconfig')[server_name].setup({})
    end,
  },
})
require('telescope').setup{
  defaults = {
    -- Default configuration for telescope goes here:
    -- config_key = value,
    mappings = {
      i = {
        -- map actions.which_key to <C-h> (default: <C-/>)
        -- actions.which_key shows the mappings for your picker,
        -- e.g. git_{create, delete, ...}_branch for the git_branches picker
		["<C-T>"] = "which_key"
      }
    }
  },
  pickers = {
    -- Default configuration for builtin pickers goes here:
    -- picker_name = {
    --   picker_config_key = value,
    --   ...
    -- }
    -- Now the picker_config_key will be applied every time you call this
    -- builtin picker
  },
  extensions = {
    -- Your extension configuration goes here:
    -- extension_name = {
    --   extension_config_key = value,
    -- }
    -- please take a look at the readme of the extension you want to configure
  }
}
