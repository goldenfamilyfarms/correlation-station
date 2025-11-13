## Description

<!-- Provide a brief description of the changes in this PR -->

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring
- [ ] Configuration change
- [ ] Dependency update

## Related Issues

<!-- Link to related issues using #issue-number -->

Closes #

## Changes Made

<!-- List the specific changes made in this PR -->

-
-
-

## Testing Performed

<!-- Describe the testing you have performed -->

- [ ] Unit tests pass (`pytest`)
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Tested on local environment
- [ ] Tested on dev environment
- [ ] Load/stress testing (if applicable)

### Test Commands Run

```bash
# Add commands you ran to test this change
make test
make build
make up
make health
```

## Configuration Changes

<!-- List any configuration changes (environment variables, config files, etc.) -->

- [ ] Updated `.env.example`
- [ ] Updated documentation
- [ ] No configuration changes required

## Deployment Notes

<!-- Any special instructions for deploying this change -->

- [ ] Requires database migration
- [ ] Requires service restart
- [ ] Requires new environment variables
- [ ] Can be deployed without downtime
- [ ] No special deployment steps needed

## Checklist

### Code Quality

- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings or errors
- [ ] I have added tests that prove my fix is effective or that my feature works
- [ ] New and existing unit tests pass locally with my changes

### Security

- [ ] I have checked for security vulnerabilities
- [ ] No secrets or credentials are exposed in the code
- [ ] Dependencies have been scanned for vulnerabilities
- [ ] Security best practices have been followed

### Observability

- [ ] Added appropriate logging
- [ ] Added metrics/instrumentation if needed
- [ ] Added tracing/spans for new operations
- [ ] Updated dashboards if needed
- [ ] Added alerts if needed

### Documentation

- [ ] README updated (if applicable)
- [ ] API documentation updated (if applicable)
- [ ] Runbook updated (if applicable)
- [ ] Architecture diagrams updated (if applicable)
- [ ] Comments added to complex code sections

## Screenshots/Recordings

<!-- Add screenshots or recordings to help explain your changes (if applicable) -->

## Additional Context

<!-- Add any other context about the PR here -->

## Reviewers

<!-- Tag specific people for review -->

@SRE-team @sense-dev-team

---

## Post-Merge Checklist

- [ ] Verify deployment to dev
- [ ] Monitor logs for errors
- [ ] Check metrics/dashboards
- [ ] Update project board/tracking
- [ ] Notify team in Slack #observability-updates