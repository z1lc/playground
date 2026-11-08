## About
`playground` is a repository that holds an assortment of small, individual tools, built together with AI coding agents like Claude Code. Each is in its own directory. The repo is then deployed to GitHub pages, so that users can interact with the tools / pages through a regular web browser.

A few pointers:
 * When developing within the repo, ensure that the HTML files can be served from GitHub Pages. 
 * `_config.yml` keeps source and data files (`.md`, `.py`, `.json`, `.mjs`, `.yaml`, `.pdf`, ...) off the published site. If a page loads one of those at runtime (e.g. `fetch('data.json')`), add its file name under `include:` there (Pages' Jekyll matches `include` by file name only, not folder path). The repo is public, so excluded files are still readable on GitHub.
 * If you develop a new tool, make sure to add it to the directory in the index.
 * If a tool has a user-interactive part, make sure all parts are by-default saved to localStorage and persist through refreshes.