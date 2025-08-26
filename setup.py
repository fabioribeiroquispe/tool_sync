from setuptools import setup, find_packages

setup(
    name='tool_sync',
    version='0.3.3',
    author='Fábio Ribeiro dos Santos Quispe',
    author_email='fabiorisantos1981@gmail.com',
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    entry_points={
        'console_scripts': [
            'tool_sync=tool_sync.main:main',
        ],
    },
    description='A bidirectional synchronization tool for Azure DevOps work items.',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/fabioribeiroquispe/tool_sync',
    keywords=['azure devops', 'sync', 'synchronization', 'work items'],
    license='MIT',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
    ],
)
