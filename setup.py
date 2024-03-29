from setuptools import setup, find_packages

setup(
    name='robot_azure_sync',
    version='1.0.0',
    author='Fábio Ribeiro dos Santos Quispe',
    author_email='fabiorisantos1981@gmail.com',
    packages=find_packages(),
    install_requires=[
        'requests',
    ],
    entry_points={
        'console_scripts': [
            'robot_azure_sync=robot_azure_sync.robot_azure_sync:robot_azure_sync',
        ],
    },
    description='Synchronization functionalities for Azure-related tasks.',
    long_description=open('README.md', encoding='utf-8').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/fabiorisantosquispe/robot_azure_sync',
    keywords=['SYNC', 'SYNCHRONIZATION', 'ROBOT FRAMEWORK', 'AZURE'],
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)
