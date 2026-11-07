# Publish Memingo for VS Code

## One-time Marketplace setup

1. Create an Azure DevOps organization.
2. Create a Visual Studio Marketplace publisher.
3. Create a Personal Access Token with **Marketplace: Manage** permission.
4. Open the GitHub repository settings and add a secret named `VSCE_PAT`.
5. Confirm that `publisher` in `package.json` matches the Marketplace publisher ID.

## Package locally

From the repository root:

```bash
cd vscode-extension
npx @vscode/vsce package
npx @vscode/vsce ls-publishers
```

A `.vsix` file can be installed directly in VS Code with **Extensions: Install from VSIX...**.

## Publish through GitHub

Create a GitHub Release, or run the **Publish VS Code Extension** workflow manually. The workflow packages the extension, uploads the VSIX to the Release workflow run, and publishes it when `VSCE_PAT` is available.

## Publishing without a release

```bash
cd vscode-extension
npx @vscode/vsce login <publisher-id>
# Enter the PAT when prompted
npx @vscode/vsce publish
```
