.PHONY: firmware test app check
firmware:
	python3 scripts/build-firmware.py
test:
	python3 scripts/test-firmware.py
	scripts/swift-local.sh test
app:
	scripts/build-macos-app.sh
check: test
