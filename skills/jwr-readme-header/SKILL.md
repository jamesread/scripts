---
name: jwr-readme-header
description: Updates README headers to match a standard format, including project name, description, badges, and logo.
---

Ensure that the README file has a consistent header format that includes the project logo, name, description, and relevant badges. The header should be centered and visually appealing to provide a clear introduction to the project.

If logo.svg is not present in the repository at the root, check if there is a logo.svg file in a subdirectory (eg: frontend/assets/logo.svg) and copy that file to the root of the repository. If no logo.svg file is found, create a simple placeholder logo (e.g., a colored square with the project initials) and save it as logo.svg in the root of the repository.

This is a template for the README header with a project called OliveTin:


```
<div align = "center">
  <img alt = "project logo" src = "logo.svg" width = "128" />
  <h1>OliveTin</h1>

  OliveTin gives **safe** and **simple** access to predefined shell commands from a web interface.

[![Maturity Badge](https://img.shields.io/badge/maturity-Production-brightgreen)](#none)
[![Discord](https://img.shields.io/discord/846737624960860180?label=Discord%20Server)](https://discord.gg/jhYWWpNJ3v)
[![Awesome](https://cdn.rawgit.com/sindresorhus/awesome/d7305f38d29fed78fa85652e3a63e154dd8e8829/media/badge.svg)](https://github.com/awesome-selfhosted/awesome-selfhosted#automation)

[![Go Report Card](https://goreportcard.com/badge/github.com/Olivetin/OliveTin)](https://goreportcard.com/report/github.com/OliveTin/OliveTin)

</div>
```

The remainder of the README should be left unchanged. Only update the header section as described above.

The example above shows "OliveTin", but the project name should be updated to match the actual project name. The description should also be updated to match the actual project description. The badges should be updated to reflect the actual badges for the project.

Badges that are not relevant to the project should be removed. If there are relevant badges that are not included in the template, they should be added to the header.
