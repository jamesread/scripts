local M = {}

function M.apply()
	vim.api.nvim_set_hl(0, "DiffAdd",    { bg = "#CDEB8B" })
	vim.api.nvim_set_hl(0, "DiffDelete", { bg = "#EB8B9D" })
	vim.api.nvim_set_hl(0, "DiffChange", { bg = "#EBC78B" })
	vim.api.nvim_set_hl(0, "DiffText",   { bg = "#FFB977" })
	vim.api.nvim_set_hl(0, "DiffviewFilePanelFileName",  { bg = "#CDEB8B" })
end

return M
