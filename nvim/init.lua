vim.o.number = true
vim.o.relativenumber = true
vim.o.termguicolors = false
vim.o.tabstop = 4

require("config.lazy")

vim.keymap.set("n", "<S-R>", ":Neotree action=focus reveal=true<CR>", { noremap = true, silent = true })
vim.cmd.set("background=light")
vim.cmd.colorscheme("vim")
