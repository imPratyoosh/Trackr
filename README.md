<img
    src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=28&duration=2200&pause=1200&color=FACC15&center=false&vCenter=false&width=800&lines=Track+repositories+releases+easily.;Never+miss+an+update.;Track+multiple+projects.;Built+for+release+hunters."
    alt="Typing SVG"
  />


## About 
This is a modular repository, used to track updates of various GitHub repositories.
+ `check.yml` runs every hour and searches for new releases and if found it'll be automatically published in this repository with it's release notes.

Adding more repositories is very simple.
You just need to add new TOML table in `tracker.toml`.

## Structure
```
[Repo-name] # used in release titles.

enabled = "true" # default "true", if set to `false`, that repository won't be tracked.
group = "group-name" # group name used to combine multiple repos as groups.
repo = "owner/repo-name" # owner name and repository name of target.
track = "stable" # used to specify release type to track, default `stable`, `dev` (pre-releases only), `latest.

```
