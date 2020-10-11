import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
	name='kotacon',
	version='1.0.0',
	author="Sysfian Solutions",
	author_email="spencer@sysfiansolutions.com",
	description="Controller Interface for the Minn-Kota Power Drive Trolling Motor",
	long_description=long_description,
	packages=setuptools.find_packages(),
	include_package_data=True,
	zip_safe=False,
	install_requires=[
		'gpiozero',
		'adafruit-circuitpython-dht',
		'pyserial',
		'rpi_rf',
		'py_qmc5883l'
	],
)