from setuptools import setup, find_packages

setup(
    name='APITesterByHackercd',
    version='1.0.2',
    description='API自动化测试框架',
    author='Hackercd',
    author_email='Hackercd@foxmail.com',
    packages=find_packages(exclude=['tests', 'test_cases', 'docs']),
    install_requires=[
        'requests>=2.25.0',
        'pytest>=6.0.0',
        'pydantic>=1.8.0',
        'python-dotenv>=0.19.0',
        'PyYAML>=6.0',
        'openpyxl>=3.0.9',
        'allure-pytest>=2.13.0'
    ],
    include_package_data=False,
    zip_safe=False
)