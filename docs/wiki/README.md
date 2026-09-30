# Wiki pages

The pages of the GitHub wiki (https://github.com/zmeel/qpcr-assay-check/wiki), kept here so they
are reviewed and versioned with the code. File name = wiki page name (`Home.md` is the start
page, `_Sidebar.md` the navigation). To publish, either paste each file into a wiki page of the
same name, or push them to the wiki's own repository:

```
git clone https://github.com/zmeel/qpcr-assay-check.wiki.git
cp docs/wiki/*.md qpcr-assay-check.wiki/ && rm qpcr-assay-check.wiki/README.md
cd qpcr-assay-check.wiki && git add . && git commit -m "Update wiki" && git push
```

The wiki repository exists only after its first page has been created on GitHub.
