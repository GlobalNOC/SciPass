NAME=SciPass
VERSION=1.0.0

rpm:	dist
	rpmbuild -ta dist/$(NAME)-$(VERSION).tar.gz
	rm -rf dist

clean:
	rm -rf dist/$(NAME)-$(VERSION)
	rm -rf dist

dist:
	rm -rf dist/$(NAME)-$(VERSION)
	mkdir -p dist/$(NAME)-$(VERSION)
	cp -r etc/ python/ SciPass.spec dist/$(NAME)-$(VERSION)/
	cd dist; tar -czvf $(NAME)-$(VERSION).tar.gz $(NAME)-$(VERSION)/ --exclude .svn