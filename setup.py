import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("CHANGELOG.md", "r") as fh:
    long_description += fh.read()

setuptools.setup(
    name="simulus",
    version="1.1.0",
    author="Jason Liu",
    author_email="jasonxliu2010@gmail.com",
    description="A Discrete-Event Simulator in Python",
    license='MIT',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="http://people.cis.fiu.edu/liux/research/simulus/",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=['greenlet', 'runstats'],
    python_requires='>=2.8',
)
