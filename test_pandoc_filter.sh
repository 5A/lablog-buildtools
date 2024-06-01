pandoc test/test.md --lua-filter=post_filter.lua -M image-base-path=/static/image-root/ -M link-base-path=/static/link-root/ -o test/test.html
