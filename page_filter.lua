-- Pandoc lua-filter used when building page HTMLs

-- BEGIN: this filter accepts parameters from the command line and do the following:
-- 1. modifies the image source paths in the generated HTML
-- 2. modifies the link paths in the generated HTML

-- USAGE:
--  pandoc input.md
--      --lua-filter=page_filter.lua
--      -M image-base-path=/static/page-root/
--      -M link-base-path=/static/page-root/
--      -o output.html

-- Declare a variable to hold the base path
local img_base_path = ""
local link_base_path = ""

-- Function to handle metadata
function Meta(meta)
    -- Check if 'image-base-path' is provided in the metadata
    if meta["image-base-path"] then
        img_base_path = pandoc.utils.stringify(meta["image-base-path"])
        -- Debug print statement to verify the base path
        print("Image base path set to:", img_base_path)
    end
    -- Check if 'link-base-path' is provided in the metadata
    if meta["link-base-path"] then
        link_base_path = pandoc.utils.stringify(meta["link-base-path"])
        -- Debug print statement to verify the base path
        print("Link base path set to:", link_base_path)
    end
end

-- Function to modify image sources
local function modify_image_sources(elem)
    if elem.t == "Image" then
        -- Prepend the base path to the original src
        -- You can also do other transformations here
        elem.src = img_base_path .. elem.src
        -- Debug print statement to verify the change
        print("Mapped image src to:", elem.src)
    end
    return elem
end

-- Function to modify link sources
local function modify_link_sources(elem)
    if elem.t == "Link" then
        -- Prepend the base path to the original src
        -- You can also do other transformations here
        elem.target = link_base_path .. elem.target
        -- Debug print statement to verify the change
        print("Mapped link target to:", elem.target)
    end
    return elem
end

-- Function to process the entire document
function Pandoc(doc)
    -- Apply the modification to all blocks in the document
    for i, block in ipairs(doc.blocks) do
        doc.blocks[i] = pandoc.walk_block(block, {
            Image = modify_image_sources,
            Link = modify_link_sources
        })
    end
    return doc
end

-- END
