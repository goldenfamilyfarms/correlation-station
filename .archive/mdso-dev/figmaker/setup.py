import ast
from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('src/figmaker/__init__.py') as f:
    mod = ast.parse(f.read())
for node in ast.iter_child_nodes(mod):
    if not isinstance(node, ast.Assign):
        continue
    if node.targets[0].id == '__version__':
        version = ast.literal_eval(node.value)
    if node.targets[0].id == '__author__':
        author = ast.literal_eval(node.value)
    if node.targets[0].id == '__author_email__':
        author_email = ast.literal_eval(node.value)

setup(
    name="figmaker",
    version=version,
    author=author,
    author_email=author_email,
    description="Make fig.yml from version.json",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://git.blueplanet.com/blueplanet/devtools/figmaker",
    install_requires=[
        'jinja2==2.11.1',
        "MarkupSafe==1.1.1",
        "gitpython==3.1.0"
    ],
    package_data={
        "": ["*.j2"],
    },
    package_dir={'': 'src'},
    packages=find_packages(
        where='src'
    ),
    entry_points={
        'console_scripts': [
            'figmaker = figmaker.main:main',
            'get_image_tag = figmaker.main:get_image_tag',
            'get_image_vendor = figmaker.main:get_image_vendor',
        ]
    },
)
