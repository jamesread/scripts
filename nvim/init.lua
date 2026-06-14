vim.g.mapleader = "\\"
vim.g.maplocalleader = "\\"

vim.o.number = true
--vim.o.conceallevel = 2
vim.o.relativenumber = true
vim.o.termguicolors = true
vim.o.tabstop = 4
vim.o.softtabstop = 4
vim.o.shiftwidth = 4
vim.o.expandtab = true
vim.o.wrap = false

vim.opt.diffopt:append("algorithm:histogram")
vim.opt.diffopt:append("linematch:60")

vim.api.nvim_create_autocmd("FileType", {
  pattern = { "javascript", "yaml" },
  callback = function()
    vim.opt_local.tabstop = 2
    vim.opt_local.softtabstop = 2
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

vim.cmd.colorscheme("vim")
vim.cmd.set("background=light")
vim.api.nvim_set_hl(0, "Normal",		{ bg = "none" })
vim.api.nvim_set_hl(0, "NormalNC",		{ bg = "none" })
vim.api.nvim_set_hl(0, "SignColumn",	{ bg = "none" })
vim.api.nvim_set_hl(0, "EndOfBuffer",	{ bg = "none" })
vim.api.nvim_set_hl(0, "Statement",		{ bg = "none",		fg = "#BB7721" })
vim.api.nvim_set_hl(0, "Constant",		{ bg = "none",		fg = "#D60429" })
vim.api.nvim_set_hl(0, "Identifier",	{ bg = "none",		fg = "#000000" })
vim.api.nvim_set_hl(0, "Type",			{ bg = "none",		fg = "#2E8B57" })
vim.api.nvim_set_hl(0, "Special",		{ bg = "none",		fg = "#bb0000", bold = false })
vim.api.nvim_set_hl(0, "PreProc",		{ bg = "none",		fg = "#6A0DAD", bold = true })

vim.api.nvim_set_hl(0, "LineNr", { fg = "#888888" })

require("diffcolors").apply()
