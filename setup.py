import setuptools

with open("README.rst", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="spylls",
    version="0.1.0",
    author="Victor Shepelev",
    author_email="zverok.offline@gmail.com",
    description="Hunspell ported to pure Python",
    long_description=long_description,
    url="https://github.com/zverok/spylls",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: Science/Research",

        "License :: OSI Approved :: MIT License",

        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",

        "Operating System :: OS Independent",

        "Topic :: Text Processing :: Linguistic"
    ],
    python_requires='>=3.7',
    keywords=["hunspell", "spelling", "spellcheck", "suggest"]
)
