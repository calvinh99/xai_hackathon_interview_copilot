### Give Critique
Go through our staged changes if you haven't already and give a brutally honest critique of bad code:
1. ie duplicate logic in multiple code locations
2. hardcoded adhoc code rather than building or extending a scalable system
3. just bad organization (ie one file handling multiple responsibilities, we want isolated logic/responsibilities in each file and to import)

### Mindset
Ask yourself if you're reinventing the wheel and something that does this already exists in our codebase, ask yourself "is this really the simplest or most code efficient way to do this? Am I writing 100 lines of code for something that can be done in 10 lines?". Code Quality is more important than just implementing the feature - it enhances future development speed and reduces tech debt.

### Delete Slop
Check the diff against previous commit, and delete all sloppy code.

This includes:
- Extra comments that a human wouldn't add or is inconsistent with the rest of the file
- Extra defensive checks or try/catch blocks that are abnormal for that area of the codebase (especially if called by trusted / validated codepaths)
- Casts to any to get around type issues
- Variables that are only used a single time right after declaration, prefer inlining the rhs.
- Any other style that is inconsistent with the file

### Summarize
Report at the end with only a 1-3 sentence summary of what you changed