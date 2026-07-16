# Makefile for pam_btotp.so PAM module
# BetterTOTP - Time-based one-time passwords with alphanumeric+special output

CC ?= gcc
CFLAGS = -Wall -Wextra -O2 -fPIC -D_GNU_SOURCE
LDFLAGS = -shared
LIBS = -lpam -lcrypto

TARGET = pam_btotp.so
SRC = pam_btotp.c

# Detect PAM module directory
PAMDIR := $(shell if [ -d /lib/x86_64-linux-gnu/security ]; then \
    echo /lib/x86_64-linux-gnu/security; \
elif [ -d /lib/security ]; then \
    echo /lib/security; \
elif [ -d /usr/lib/security ]; then \
    echo /usr/lib/security; \
else \
    echo /lib/security; \
fi)

.PHONY: all clean install uninstall test

all: $(TARGET)

$(TARGET): $(SRC)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $< $(LIBS)

clean:
	rm -f $(TARGET)

install: $(TARGET)
	install -d $(DESTDIR)$(PAMDIR)
	install -m 755 $(TARGET) $(DESTDIR)$(PAMDIR)/$(TARGET)
	@echo ""
	@echo "Installed $(TARGET) to $(DESTDIR)$(PAMDIR)/"
	@echo ""
	@echo "Add to /etc/pam.d/sshd:"
	@echo "  auth required pam_btotp.so nullok"
	@echo ""

uninstall:
	rm -f $(DESTDIR)$(PAMDIR)/$(TARGET)

test: $(TARGET)
	@echo "Build successful. Test with:"
	@echo "  btotp init"
	@echo "  btotp add test-account -g"
	@echo "  btotp enroll test-account"
	@echo "  pamtester sshd \$$USER authenticate"
