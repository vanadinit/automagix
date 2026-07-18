from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='automagix',
    version='4.0.0.dev1',
    description='Automation wrapper for bash and python commands',
    keywords=['bash', 'shell', 'command', 'automation', 'process', 'wrapper', 'devops', 'system administration'],
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://codeberg.org/vanadinit/automagix',
    author='Johannes Paul',
    author_email='vanadinit@quantentunnel.de',
    license='MIT',
    python_requires='>=3.10',
    install_requires=[
        'pyyaml>=5.1',
    ],
    extras_require={
        'tests': ['cython<3.0.0', 'pytest', 'pytest-docker', 'flake8'],
        'bash completion': ['argcomplete'],
    },
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'automagix=automagix:main',
            'automagix-manager=automagix.parallel:run_manager',
            'automagix-from-file=automagix.parallel:run_auto_from_file',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)
