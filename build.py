import subprocess
import json
import os
import shutil
from datetime import datetime
import logging
# This package
from lablog_api import LablogAPI
from data_model import PostMetadata
from config import load_config_from_file, BuildConfig
from logging_formatter import BuildtoolsLogFormatter

# configure root logger to output all logs to stdout
lg = logging.getLogger()
lg.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(BuildtoolsLogFormatter())
lg.addHandler(ch)
# configure logger for this module.
lg = logging.getLogger(__name__)


class LablogPostBuilder:
    def __init__(self, post_path: str, config: BuildConfig) -> None:
        self.pcfg = config.paths
        self.post_path = post_path
        self.temp_dir = self.pcfg.temporary_files_directory
        # load metadata
        lg.info(f"Loading metadata for post at {post_path}")
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
        self.perm_link = self.pcfg.posts_web_root_location + \
            self.post_meta.root + ".html"
        self.share_post_preset = self.perm_link

    def pandoc_convert_post_to_html(self):
        file_in = f"{self.post_path}/post.md"
        file_out: str = self.temp_dir + "post_content.html"
        args = ['./bin/pandoc.exe', file_in,
                '--lua-filter', './post_filter.lua',
                '-M', f'image-base-path=/static/{self.post_meta.root}/',
                '-M', f'link-base-path=/static/{self.post_meta.root}/',
                '-o', file_out]
        pandoc_result = subprocess.run(args, capture_output=True)
        lg.info("PANDOC OUTPUT: ")
        lg.info(pandoc_result.stdout.decode())
        lg.info("END OF PANDOC OUTPUT")

    def insert_html_into_template(self, post_template: str, output_directory: str):
        # Read HTML containing content of the post
        lg.info("Reading HTML fragment from temporary file")
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
            COMMENTS_LOCATION=self.pcfg.comment_API_base_location + self.post_meta.post_id
        )

        file_out = output_directory + self.post_meta.root + ".html"
        lg.info(f"Writing templated HTML source to {file_out}")
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

    def copy_static_files(self):
        # select all directories in post folder
        directories_in = [d for d in next(os.walk(self.post_path))[1]]
        if len(directories_in) == 0:
            lg.info("No static files found, skipping.")
            return
        lg.info(f"Copying static files from: {directories_in}")
        directory_out = f"{
            self.pcfg.static_files_output_directory}{self.post_meta.root}/"
        lg.info(f"COPY TO: {directory_out}")
        if os.path.exists(directory_out):
            lg.warning(
                f"Directory {directory_out} already exists, deleting it before copying.")
            shutil.rmtree(directory_out)
        os.makedirs(directory_out, exist_ok=True)
        for directory in directories_in:
            copy_from = self.post_path + '/' + directory
            copy_to = directory_out + directory
            lg.info(f"Copying from {copy_from} to {copy_to}")
            shutil.copytree(copy_from, copy_to)


class LablogBuilder:
    def __init__(self) -> None:
        lg.info("Loading buildtools config from config.json")
        self.config = load_config_from_file()
        lg.info("Config loaded.")
        self.pcfg = self.config.paths
        # Load template
        lg.info(f"Loading template file from {self.pcfg.post_template_file}")
        with open(self.pcfg.post_template_file, 'rb') as f:
            self.post_template = f.read().decode('utf-8')
        lg.info("Connecting to Lablog API")
        self.api = LablogAPI()
        lg.info(f"API Connected, scanning for posts from {
                self.pcfg.posts_input_directory}")
        self.post_paths = [self.pcfg.posts_input_directory +
                           d for d in next(os.walk(self.pcfg.posts_input_directory))[1]]
        lg.debug("Posts found: ")
        for post_path in self.post_paths:
            lg.debug(post_path)

    def build_posts(self):
        lg.warning("Start to build all posts...")

        sitemap = []

        for post_path in self.post_paths:
            lg.warning(f"Building post from {post_path}")
            pb = LablogPostBuilder(post_path=post_path, config=self.config)
            lg.info("Calling pandoc to convert post MD to HTML fragment")
            pb.pandoc_convert_post_to_html()
            lg.info(
                "Conversion done, registering the post at remote server backend...")
            pb.register_post_at_backend(self.api)
            lg.info("Registering OK, constructing HTML source from template")
            pb.insert_html_into_template(
                post_template=self.post_template,
                output_directory=self.pcfg.posts_output_directory)
            lg.info("HTML source built, copying static files to output")
            pb.copy_static_files()
            sitemap.append(pb.perm_link)

        lg.warning("All posts built.")

        lg.info(f"Writing sitemap.txt to {self.pcfg.sitemap_output_file}")
        with open(self.pcfg.sitemap_output_file, 'wb') as f:
            f.write('\n'.join(sitemap).encode('utf-8'))

        lg.info(f"Writing buffered post information to {
                self.pcfg.buffered_posts_json_file}")
        with open(self.pcfg.buffered_posts_json_file, 'wb') as f:
            f.write(json.dumps(self.api.get_posts()).encode('utf-8'))

        lg.info(f"Calling npm build in working dir {
                self.pcfg.npm_build_working_directory}")
        npm_build_result = subprocess.run(
            ['npm', 'run', 'build'], cwd=self.pcfg.npm_build_working_directory, shell=True)
        print(npm_build_result)

    def deploy(self):
        lg.warning("Deploying build results to remote server")
        lg.warning("Copying files...")
        subprocess.run(
            ['scp', '-r', self.pcfg.frontend_dist_files,
                self.pcfg.remote_html_directory],
            shell=True)


lb = LablogBuilder()
lb.build_posts()
lb.deploy()
