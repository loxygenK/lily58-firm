flash:
	@echo "Lily58 Pro has two distinct microprocessor, so writing will be launched twice!"
	@echo
	@echo "<<<<< LEFT"
	qmk flash
	@echo "      RIGHT >>>>>"
	qmk flash
	@echo "All done! Restore your USB connection to left microprocessor."

image:
	python3 scripts/img2c.py

link-local:
	bash "./scripts/link-local.sh"








# vim: set ft=make:
