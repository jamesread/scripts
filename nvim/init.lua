vim.o.number = true
vim.o.conceallevel = 2
vim.o.relativenumber = true
vim.o.termguicolors = false
vim.o.tabstop = 4
vim.o.softtabstop = 4
vim.o.shiftwidth = 4
vim.o.wrap = false

vim.api.nvim_create_autocmd("FileType", {
  pattern = "javascript",
  callback = function()
	vim.opt_local.expandtab = true
	vim.opt_local.shiftwidth = 2
  end,
})

vim.api.nvim_create_autocmd("FileType", {
  pattern = "yaml",
  callback = function()
    vim.opt_local.expandtab = true
	vim.opt_local.shiftwidth = 2
  end,
})

require("config.lazy")

vim.keymap.set("n", "<S-R>", ":Neotree action=focus reveal=true<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "<S-E>", ":Neotree action=close<CR>", { noremap = true, silent = true })
vim.keymap.set("n", "<C-P>", ":bp<cr>", { noremap = true, silent = true})
vim.keymap.set("n", "<C-N>", ":bn<cr>", { noremap = true, silent = true})
vim.keymap.set("n", "<C-T>", ":Telescope lsp_document_symbols<cr>", { noremap = true, silent = true})
vim.keymap.set("n", "<C-F>", ":Telescope find_files<cr>", { noremap = true, silent = true})
vim.keymap.set("n", "<C-R>", ":Telescope lsp_references<cr>", { noremap = true, silent = true})
vim.keymap.set("n", "<C-S>", ":Telescope lsp_document_symbols symbols=function,method<cr>", { noremap = true, silent = true})
vim.keymap.set("n", "<C-B>", ":Telescope buffers<cr>", { noremap = true, silent = true})
vim.keymap.set("n", "<C-O>", ":ObsidianSearch<cr>", { noremap = true, silent = true})
vim.keymap.set("n", "<C-I>", ":ObsidianTags<cr>", { noremap = true, silent = true})
vim.keymap.set("n", "<leader>ca", vim.lsp.buf.code_action, { noremap = true, silent = true })
vim.api.nvim_set_keymap("n", "<S-K>", "i[text](url)<Esc>2hi", { noremap = true, silent = true })
vim.api.nvim_set_keymap("v", "<leader>k", '"sy<ESC>`<v`>s[<C-r>s](url)<Left>', { noremap = true, silent = true })

vim.cmd.set("background=light")
vim.cmd.colorscheme("vim")


local cmp = require'cmp'

cmp.setup({
	snippet = {
		expand = function(args)
			vim.snippet.expand(args.body)
		end,
	},
	mapping = cmp.mapping.preset.insert({
		['<CR>'] = cmp.mapping.confirm({ select = true }),
	})
})

require("refactoring").setup()
require("nvim-treesitter").setup()

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
      vim.lsp.config[server_name].setup({})
    end,
  },
})

local sorters = require('telescope.sorters')

require('telescope').setup{
  defaults = {
	defaults = {
		sorting_strategy = "ascending",
	},
	pickers = {
		lsp_document_symbols = {
			sorter = sorters.get_generic_fuzzy_sorter(),
			sorting_strategy = "ascending",
		},
	},
    mappings = {
      i = {
   		["<C-T>"] = "which_key"
      }
    }
  },
  extensions = {
	  ["ui-select"] = {
	    require("telescope.themes").get_dropdown {
	      -- even more opts
	    }
	  }
    -- Your extension configuration goes here:
    -- extension_name = {
    --   extension_config_key = value,
    -- }
    -- please take a look at the readme of the extension you want to configure
  }
}

require("telescope").load_extension("ui-select")

require("nvim-treesitter").setup()
require("refactoring").setup()
-- require("opencode").setup()


require("diffcolors").apply()
