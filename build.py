import subprocess
import json
import os
from datetime import datetime

# This package
from lablog_api import LablogAPI
from data_model import PostMetadata
from config import load_config_from_file


class LablogPostBuilder:
    def __init__(self, post_path: str, temp_dir: str = "./temp/") -> None:
        self.post_path = post_path
        self.temp_dir = temp_dir
        # load metadata
        file_in = f"{post_path}/meta.json"
        with open(file_in, 'rb') as f:
            post_meta = f.read().decode('utf-8')
            post_meta = json.loads(post_meta)
        self.post_meta = PostMetadata(**post_meta)
        # Convert date data to HTML standards
        if self.post_meta.datetime is not None:
            post_time = datetime.strptime(
                self.post_meta.datetime, "%Y-%m-%d %H:%M:%S")
        elif self.post_meta.timestamp is not None:
            post_time = datetime.fromtimestamp(self.post_meta.timestamp)
        else:
            raise ValueError(
                "Datetime info cannot be found for post at dir {}".format(post_path))
        self.post_time = post_time
        self.post_date_machine_readable = post_time.strftime("%Y-%m-%d")
        self.post_date_str = post_time.strftime("%B %d, %Y")
        # deal with optional fields
        if self.post_meta.catagory is None:
            self.post_meta.catagory = "Miscellaneous"
        if self.post_meta.tags is None:
            self.post_meta.tags = []
        # Create perm link to insert into share buttons
        self.perm_link = "https://zzi.io/posts/" + \
            self.post_meta.root + ".html"
        self.share_post_preset = self.perm_link

    def pandoc_convert_post_to_html(self):
        file_in = f"{self.post_path}/post.md"
        file_out: str = self.temp_dir + "post_content.html"
        args = ['./bin/pandoc.exe', file_in, '-o', file_out]
        pandoc_result = subprocess.run(args, capture_output=True)
        print(pandoc_result)

    def insert_html_into_template(self, post_template: str, output_directory: str):
        # Read HTML containing content of the post
        file_in = self.temp_dir + "post_content.html"
        with open(file_in, 'rb') as f:
            post_content = f.read().decode('utf-8')

        # Fill the template using python's templating system
        filled_result = post_template.format(
            BLOG_POST_TITLE=self.post_meta.title,
            BLOG_POST_AUTHOR=self.post_meta.author,
            AUTHOR_EMAIL=self.post_meta.email,
            BLOG_POST_DATE_MACHINE_READABLE=self.post_date_machine_readable,
            BLOG_POST_DATE_STRING=self.post_date_str,
            BLOG_POST_CONTENT=post_content,
            BLOG_POST_TAGS_STRING=", ".join(self.post_meta.tags),
            BLOG_POST_CATAGORY=self.post_meta.catagory,
            SHARE_POST_PRESET=self.share_post_preset,
            BLOG_POST_ID=self.post_meta.post_id,
            COMMENTS_LOCATION="http://dev.zzi.io:8000/comments/" + self.post_meta.post_id
        )

        file_out = output_directory + self.post_meta.root + ".html"
        with open(file_out, 'wb') as f:
            f.write(filled_result.encode('utf-8'))

    def register_post_at_backend(self, api: LablogAPI) -> str:
        data = dict()
        data["title"] = self.post_meta.title
        data["abstract"] = self.post_meta.abstract
        data["link"] = "/posts/" + \
            self.post_meta.root + ".html"
        data["created_timestamp"] = self.post_time.timestamp()
        data["catagory"] = self.post_meta.catagory
        data["tags"] = self.post_meta.tags
        if self.post_meta.post_id:
            data["post_id"] = self.post_meta.post_id
        post_id = api.register_post(data=data)["post_id"]
        if not self.post_meta.post_id:
            # Manually created post meta file does not contain its uid,
            # because this info is only available from backend.
            # So after registering, save it back to meta.json
            self.post_meta.post_id = post_id
            with open(f"{self.post_path}/meta.json", 'wb+') as f:
                f.write(self.post_meta.model_dump_json(
                    indent=2).encode('utf-8'))
        return post_id


class LablogBuilder:
    def __init__(self) -> None:
        self.config = load_config_from_file().paths
        # Load template
        with open(self.config.post_template_file, 'rb') as f:
            self.post_template = f.read().decode('utf-8')
        self.api = LablogAPI()
        self.post_paths = [self.config.posts_input_directory +
                           d for d in next(os.walk(self.config.posts_input_directory))[1]]

    def build_posts(self):
        sitemap = []
        for post_path in self.post_paths:
            pb = LablogPostBuilder(post_path=post_path)
            pb.pandoc_convert_post_to_html()
            pb.register_post_at_backend(self.api)
            pb.insert_html_into_template(
                post_template=self.post_template,
                output_directory=self.config.posts_output_directory)
            sitemap.append(pb.perm_link)
        with open(self.config.sitemap_output_file, 'wb') as f:
            f.write('\n'.join(sitemap).encode('utf-8'))
        with open(self.config.buffered_posts_json_file, 'wb') as f:
            f.write(json.dumps(self.api.get_posts()).encode('utf-8'))

        npm_build_result = subprocess.run(
            ['npm', 'run', 'build'], cwd=self.config.npm_build_working_directory, shell=True)
        print(npm_build_result)

    def deploy(self):
        pass


lb = LablogBuilder()
lb.build_posts()
