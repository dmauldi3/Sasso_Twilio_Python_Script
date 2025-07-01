# Branch Cleanup and Merge Instructions

This document provides step-by-step instructions for cleaning up the master branch and merging the Evoice-Twillio-Hubspot-Connector branch into it to create a professional repository structure.

## 1. Clean Up the Master Branch

Follow these steps to clean up the master branch:

1. **Checkout the master branch**:
   ```
   git checkout master
   ```

2. **Create or update the .gitignore file**:
   ```
   git checkout Evoice-Twillio-Hubspot-Connector -- .gitignore
   ```

3. **Add the README.md file**:
   ```
   git checkout Evoice-Twillio-Hubspot-Connector -- README.md
   ```

4. **Add the requirements.txt file**:
   ```
   git checkout Evoice-Twillio-Hubspot-Connector -- requirements.txt
   ```

5. **Add the .env.example file**:
   ```
   git checkout Evoice-Twillio-Hubspot-Connector -- .env.example
   ```

6. **Remove sensitive files from Git tracking (but keep them locally)**:
   ```
   git rm --cached .env "private-key.pem" "aws stuff new evoice.txt"
   ```

7. **Commit these changes**:
   ```
   git commit -m "Clean up master branch: add documentation and remove sensitive files"
   ```

## 2. Merge the Branches

After cleaning up the master branch, follow these steps to merge the Evoice-Twillio-Hubspot-Connector branch into it:

1. **Ensure you're on the master branch**:
   ```
   git checkout master
   ```

2. **Merge the Evoice-Twillio-Hubspot-Connector branch**:
   ```
   git merge Evoice-Twillio-Hubspot-Connector
   ```

3. **Resolve any merge conflicts**:
   If there are merge conflicts, Git will notify you. The most likely conflict will be in the TwilioHubspotConnector.py file.

   To resolve conflicts:
   - Open the conflicted files in your editor
   - Look for conflict markers (<<<<<<< HEAD, =======, >>>>>>> Evoice-Twillio-Hubspot-Connector)
   - Edit the files to resolve the conflicts (generally, keep the code from the Evoice-Twillio-Hubspot-Connector branch as it appears to be more updated)
   - Save the files
   - Add the resolved files:
     ```
     git add .
     ```
   - Complete the merge:
     ```
     git commit -m "Merge Evoice-Twillio-Hubspot-Connector into master"
     ```

4. **Push the changes to the remote repository**:
   ```
   git push origin master
   ```

## 3. Clean Up Repository History (Optional but Recommended)

To completely remove sensitive files from the Git history:

1. **Install the BFG Repo-Cleaner** (https://rtyley.github.io/bfg-repo-cleaner/)

2. **Create a text file named `sensitive-files.txt` with the names of files to remove**:
   ```
   .env
   private-key.pem
   aws stuff new evoice.txt
   ```

3. **Run BFG to remove the files from history**:
   ```
   bfg --delete-files sensitive-files.txt
   ```

4. **Clean up and push the changes**:
   ```
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   git push --force
   ```

## 4. Delete the Redundant Branch (Optional)

After successfully merging, you may want to delete the Evoice-Twillio-Hubspot-Connector branch:

1. **Delete the local branch**:
   ```
   git branch -d Evoice-Twillio-Hubspot-Connector
   ```

2. **Delete the remote branch**:
   ```
   git push origin --delete Evoice-Twillio-Hubspot-Connector
   ```

## 5. Verify the Repository Structure

After completing these steps, your repository should have a clean, professional structure with:

- A comprehensive README.md
- A proper .gitignore file
- A requirements.txt file
- An .env.example file as a template for configuration
- No sensitive files in the repository
- A single, clean branch (master)

You can verify this with:
```
git ls-files
```

This should show only the non-sensitive files that should be tracked in the repository.
