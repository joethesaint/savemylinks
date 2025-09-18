# Git Branching Strategy - SaveMyLinks

## 🌳 Branch Structure Overview

This document outlines the branching strategy for the SaveMyLinks project, establishing clear workflows for development, feature integration, and production releases.

---

## 📋 Branch Hierarchy

### **Main Branches**

#### 1. `main` - Production Branch
- **Purpose**: Stable, production-ready code
- **Protection**: Protected branch, requires PR reviews
- **Deployment**: Automatically deployed to production
- **Updates**: Only receives merges from `enhancements` branch

#### 2. `dev` - Secondary Main Branch (Development Hub)
- **Purpose**: Integration branch for ongoing development
- **Role**: Primary development branch where new features are integrated
- **Updates**: Receives merges from feature branches
- **Stability**: Should always be in a working state
- **Testing**: All features must pass tests before merging

#### 3. `enhancements` - Final Integration Branch
- **Purpose**: Final staging before production
- **Role**: Receives polished features from `dev` for final review
- **Updates**: Periodically updated from `dev` when features are ready for production
- **Quality Gate**: Final testing and validation before `main`

---

## 🔄 Workflow Process

### **Feature Development Workflow**

```
1. Create feature branch from `dev`
   └── feature/0x##-feature-name

2. Develop and test feature
   └── Regular commits with hex indexing

3. Create PR to merge into `dev`
   └── Code review and testing

4. Merge to `dev` after approval
   └── Feature is now part of development integration

5. Periodically merge `dev` → `enhancements`
   └── When features are ready for production staging

6. Merge `enhancements` → `main`
   └── Production release
```

### **Branch Naming Conventions**

#### Feature Branches
```
feature/0x##-brief-description
├── feature/0x13-user-authentication
├── feature/0x14-bulk-operations
└── feature/0x15-analytics-dashboard
```

#### Bugfix Branches
```
bugfix/0x##-brief-description
├── bugfix/0x16-rate-limit-fix
├── bugfix/0x17-cache-invalidation
└── bugfix/0x18-cors-headers
```

#### Hotfix Branches (Emergency fixes)
```
hotfix/0x##-brief-description
├── hotfix/0x19-security-patch
└── hotfix/0x1A-critical-bug-fix
```

---

## 🚀 Development Process

### **Starting New Development**

1. **Always branch from `dev`**:
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/0x##-feature-name
   ```

2. **Regular development**:
   ```bash
   # Make changes
   git add .
   git commit -m "[0x##] Brief description of change"
   git push origin feature/0x##-feature-name
   ```

3. **Create Pull Request**:
   - Target: `dev` branch
   - Include: Description, testing notes, changelog entry
   - Review: Required before merge

### **Integration to Production**

1. **Dev to Enhancements** (Weekly/Bi-weekly):
   ```bash
   git checkout enhancements
   git pull origin enhancements
   git merge dev
   git push origin enhancements
   ```

2. **Enhancements to Main** (Release cycles):
   ```bash
   git checkout main
   git pull origin main
   git merge enhancements
   git tag v1.x.x
   git push origin main --tags
   ```

---

## 📝 Commit Message Standards

### **Format**
```
[0x##] Brief description (50 chars max)

Detailed description of changes made.
Include any breaking changes or migration notes.

Closes: #issue-number (if applicable)
```

### **Examples**
```bash
# Feature commit
git commit -m "[0x13] Add JWT authentication system

Implemented user login/logout with JWT tokens.
Added middleware for protected routes.
Updated API documentation.

Closes: #45"

# Bug fix commit
git commit -m "[0x16] Fix rate limiting memory leak

Resolved issue where rate limit counters weren't 
being cleaned up after expiration.

Fixes: #52"

# Documentation commit
git commit -m "[0x17] Update CHANGELOG_ROADMAP.md

Added entries for authentication system and 
updated roadmap priorities for Q2 features."
```

---

## 🔒 Branch Protection Rules

### **Main Branch**
- ✅ Require pull request reviews (2 reviewers)
- ✅ Require status checks to pass
- ✅ Require branches to be up to date
- ✅ Restrict pushes to admins only
- ✅ Require signed commits

### **Dev Branch**
- ✅ Require pull request reviews (1 reviewer)
- ✅ Require status checks to pass
- ✅ Allow force pushes by admins
- ✅ Delete head branches after merge

### **Enhancements Branch**
- ✅ Require pull request reviews (1 reviewer)
- ✅ Require status checks to pass
- ✅ Restrict pushes to maintainers

---

## 🧪 Testing Requirements

### **Before Merging to Dev**
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Code coverage > 80%
- [ ] Linting passes
- [ ] No security vulnerabilities

### **Before Merging to Enhancements**
- [ ] All dev requirements met
- [ ] End-to-end tests pass
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] CHANGELOG_ROADMAP.md updated

### **Before Merging to Main**
- [ ] All enhancement requirements met
- [ ] Production deployment tested
- [ ] Security audit completed
- [ ] Backup procedures verified
- [ ] Rollback plan documented

---

## 📊 Release Management

### **Version Numbering**
- **Major**: Breaking changes (v2.0.0)
- **Minor**: New features (v1.1.0)
- **Patch**: Bug fixes (v1.0.1)

### **Release Process**
1. **Feature Freeze**: Stop merging new features to `enhancements`
2. **Testing Phase**: Comprehensive testing on `enhancements`
3. **Release Candidate**: Tag RC version for final testing
4. **Production Release**: Merge to `main` and tag final version
5. **Post-Release**: Monitor and prepare hotfixes if needed

### **Hotfix Process**
```bash
# Emergency fix process
git checkout main
git checkout -b hotfix/0x##-critical-fix
# Make fix
git checkout main
git merge hotfix/0x##-critical-fix
git tag v1.x.x
git checkout dev
git merge main  # Ensure fix is in dev
git checkout enhancements
git merge main  # Ensure fix is in enhancements
```

---

## 🔄 Regular Maintenance

### **Weekly Tasks**
- [ ] Merge `dev` → `enhancements` (if stable)
- [ ] Update CHANGELOG_ROADMAP.md with completed features
- [ ] Review and clean up merged feature branches
- [ ] Update project dependencies

### **Monthly Tasks**
- [ ] Security audit of dependencies
- [ ] Performance review and optimization
- [ ] Documentation review and updates
- [ ] Backup and disaster recovery testing

### **Quarterly Tasks**
- [ ] Major version planning
- [ ] Architecture review
- [ ] Technology stack evaluation
- [ ] Team process retrospective

---

## 🛠️ Tools and Automation

### **GitHub Actions**
- **CI/CD Pipeline**: Automated testing and deployment
- **Code Quality**: Automated linting and security scanning
- **Documentation**: Auto-generate API docs on releases

### **Branch Automation**
- **Auto-delete**: Feature branches after successful merge
- **Auto-update**: Keep branches in sync with upstream changes
- **Auto-tag**: Version tagging on main branch merges

---

## 📚 Quick Reference

### **Common Commands**
```bash
# Start new feature
git checkout dev && git pull && git checkout -b feature/0x##-name

# Update feature with latest dev
git checkout dev && git pull && git checkout feature/0x##-name && git merge dev

# Prepare for production
git checkout enhancements && git merge dev && git push

# Emergency hotfix
git checkout main && git checkout -b hotfix/0x##-name

# Clean up after merge
git branch -d feature/0x##-name && git push origin --delete feature/0x##-name
```

### **Branch Status Check**
```bash
# See all branches
git branch -a

# Check branch relationships
git log --oneline --graph --all -10

# See differences between branches
git diff dev..enhancements --name-only
```

---

## 🎯 Best Practices

1. **Always pull before creating new branches**
2. **Keep feature branches small and focused**
3. **Write descriptive commit messages with hex indexing**
4. **Update CHANGELOG_ROADMAP.md with each significant change**
5. **Test thoroughly before merging**
6. **Delete merged branches to keep repository clean**
7. **Use draft PRs for work-in-progress features**
8. **Tag releases consistently**
9. **Document breaking changes clearly**
10. **Communicate major changes to the team**

---

*Last Updated: Current Development Cycle*
*Document Version: 1.0*
*Maintained by: Development Team*