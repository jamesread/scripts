local M = {}

function M.apply()
--	vim.api.nvim_set_hl(0, "DiffAdd",    { bg = "#203b2a", fg = "#990000" })
--	vim.api.nvim_set_hl(0, "DiffDelete", { bg = "#3f1d1d", fg = "#00ff00" })
	vim.api.nvim_set_hl(0, "DiffChange", { bg = "#990000", fg = "#ffff00" })
	vim.api.nvim_set_hl(0, "DiffChanged", { bg = "#990000", fg = "#ffff00" })
--	vim.api.nvim_set_hl(0, "DiffText",   { bg = "#3a4a7a", fg = "#099000", bold = true })

end

-- #cake

return M
