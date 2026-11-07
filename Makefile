.PHONY: firmware test test-profile-bank app check
firmware:
	python3 scripts/build-firmware.py
test:
	python3 scripts/test-firmware.py
	python3 scripts/test-firmware.py --profile-template
	python3 scripts/run-profile-bank-tests.py
	scripts/swift-local.sh test
app:
	scripts/build-macos-app.sh
check: test
test-profile-bank:
	python3 scripts/run-profile-bank-tests.py
