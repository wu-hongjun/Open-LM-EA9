/* Native macOS research probe. Only CHECK and whitelisted memory READ exist.
 * No install, START, raw-report, reset, or flash-write operation is implemented.
 * Build: clang -std=c11 -Wall -Wextra -Werror tools/ea9_readonly_probe.c
 *        -framework IOKit -framework CoreFoundation -o /private/tmp/ea9_readonly_probe
 */
#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/hid/IOHIDManager.h>
#include <IOKit/hid/IOHIDKeys.h>
#include <IOKit/IOKitLib.h>
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { REPORT_SIZE = 64, FLASH_LIMIT = 0x20000 };
/* Qualified for the recovered stock loader's byte-copy READ. See the follow-up
 * document for register widths, complete windows and read side effects.
 * Never start a DSU snapshot at its base: that would read DCC0/DCC1 mailboxes.
 */
static const struct snapshot_window {
    const char *name;
    uint32_t address, length;
} snapshots[] = {
    {"device-id", 0x41002018, 64},
    {"nvm-status", 0x41004000, 64},
    {"user-row", 0x00804000, 64},
    {"calibration", 0x00806000, 64},
    {"port-a", 0x41004400, 128}
};
static const uint8_t magic[4] = {0x95, 0x27, 0x68, 0x18};
static uint8_t input_buffer[REPORT_SIZE];
static uint8_t reply[REPORT_SIZE];
static unsigned received;
static int invalid_reply;

static void hex(const uint8_t *p, size_t n) {
    for (size_t i = 0; i < n; ++i) printf("%02x", p[i]);
}

static void json_string(CFTypeRef value) {
    if (!value || CFGetTypeID(value) != CFStringGetTypeID()) { printf("null"); return; }
    char text[1024];
    if (!CFStringGetCString(value, text, sizeof(text), kCFStringEncodingUTF8)) {
        printf("null"); return;
    }
    putchar('"');
    for (const unsigned char *p = (const unsigned char *)text; *p; ++p) {
        if (*p == '"' || *p == '\\') { putchar('\\'); putchar(*p); }
        else if (*p < 32) printf("\\u%04x", *p);
        else putchar(*p);
    }
    putchar('"');
}

static int64_t number(IOHIDDeviceRef device, CFStringRef key) {
    CFTypeRef value = IOHIDDeviceGetProperty(device, key);
    int64_t result = -1;
    if (value && CFGetTypeID(value) == CFNumberGetTypeID())
        CFNumberGetValue(value, kCFNumberSInt64Type, &result);
    return result;
}

static void describe(IOHIDDeviceRef device) {
    uint64_t registry_id = 0;
    IORegistryEntryGetRegistryEntryID(IOHIDDeviceGetService(device), &registry_id);
    printf("{\"event\":\"device\",\"registry_id\":%" PRIu64, registry_id);
    const struct { const char *name; CFStringRef key; } strings[] = {
        {"product", CFSTR(kIOHIDProductKey)},
        {"manufacturer", CFSTR(kIOHIDManufacturerKey)},
        {"serial", CFSTR(kIOHIDSerialNumberKey)},
        {"transport", CFSTR(kIOHIDTransportKey)}
    };
    for (size_t i = 0; i < sizeof(strings)/sizeof(strings[0]); ++i) {
        printf(",\"%s\":", strings[i].name);
        json_string(IOHIDDeviceGetProperty(device, strings[i].key));
    }
    const struct { const char *name; CFStringRef key; } nums[] = {
        {"vid", CFSTR(kIOHIDVendorIDKey)}, {"pid", CFSTR(kIOHIDProductIDKey)},
        {"version", CFSTR(kIOHIDVersionNumberKey)}, {"location", CFSTR(kIOHIDLocationIDKey)},
        {"usage_page", CFSTR(kIOHIDPrimaryUsagePageKey)}, {"usage", CFSTR(kIOHIDPrimaryUsageKey)},
        {"max_input", CFSTR(kIOHIDMaxInputReportSizeKey)},
        {"max_output", CFSTR(kIOHIDMaxOutputReportSizeKey)},
        {"max_feature", CFSTR(kIOHIDMaxFeatureReportSizeKey)}
    };
    for (size_t i = 0; i < sizeof(nums)/sizeof(nums[0]); ++i)
        printf(",\"%s\":%" PRId64, nums[i].name, number(device, nums[i].key));
    CFTypeRef descriptor = IOHIDDeviceGetProperty(device, CFSTR(kIOHIDReportDescriptorKey));
    printf(",\"report_descriptor\":\"");
    if (descriptor && CFGetTypeID(descriptor) == CFDataGetTypeID())
        hex(CFDataGetBytePtr(descriptor), (size_t)CFDataGetLength(descriptor));
    printf("\"}\n");
}

static void input(void *context, IOReturn result, void *sender,
                  IOHIDReportType type, uint32_t report_id, uint8_t *data, CFIndex size) {
    (void)context; (void)sender;
    ++received;
    if (received != 1 || result != kIOReturnSuccess || type != kIOHIDReportTypeInput ||
        report_id != 0 || size != REPORT_SIZE) {
        invalid_reply = 1;
        fprintf(stderr, "Unexpected input: result=0x%x type=%d id=%u size=%ld count=%u\n",
                result, type, report_id, size, received);
        return;
    }
    memcpy(reply, data, REPORT_SIZE);
}

/* Construct from a whitelist; caller cannot provide arbitrary output bytes. */
static int allowed_read(uint32_t address) {
    if (address <= FLASH_LIMIT - REPORT_SIZE && address % REPORT_SIZE == 0) return 1;
    for (size_t i = 0; i < sizeof(snapshots)/sizeof(snapshots[0]); ++i)
        if (address >= snapshots[i].address &&
            address - snapshots[i].address < snapshots[i].length &&
            (address - snapshots[i].address) % REPORT_SIZE == 0) return 1;
    return 0;
}

static int request(IOHIDDeviceRef device, int read_request, uint32_t address) {
    uint8_t output[REPORT_SIZE] = {0};
    memcpy(output, magic, sizeof(magic));
    output[4] = output[5] = read_request ? 0x03 : 0x02;
    if (read_request) {
        if (!allowed_read(address)) return 1;
        for (unsigned i = 0; i < 4; ++i) output[6+i] = (uint8_t)(address >> (8*i));
    }
    received = 0; invalid_reply = 0;
    CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.002, false);
    if (received || invalid_reply) { fprintf(stderr, "Unsolicited report; stop session.\n"); return 1; }
    printf("{\"event\":\"request\",\"operation\":\"%s\",\"address\":%u,\"hex\":\"",
           read_request ? "READ" : "CHECK", address);
    hex(output, sizeof(output)); printf("\"}\n"); fflush(stdout);
    IOReturn result = IOHIDDeviceSetReport(device, kIOHIDReportTypeOutput, 0, output, sizeof(output));
    if (result != kIOReturnSuccess) {
        fprintf(stderr, "SetReport failed: 0x%x\n", result); return 1;
    }
    CFAbsoluteTime deadline = CFAbsoluteTimeGetCurrent() + 5.0;
    while (!received && !invalid_reply && CFAbsoluteTimeGetCurrent() < deadline)
        CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.01, false);
    if (received != 1 || invalid_reply) {
        fprintf(stderr, "Reply failed/timeout; no retries or next request.\n"); return 1;
    }
    printf("{\"event\":\"reply\",\"operation\":\"%s\",\"address\":%u,\"hex\":\"",
           read_request ? "READ" : "CHECK", address);
    hex(reply, sizeof(reply)); printf("\"}\n"); fflush(stdout);
    if (!read_request && memcmp(reply, output, 6)) {
        fprintf(stderr, "CHECK header mismatch.\n"); return 1;
    }
    return 0;
}

static int parse_number(const char *text, uint32_t *value) {
    char *end; errno = 0;
    if (!*text || *text == '-') return 1;
    unsigned long result = strtoul(text, &end, 0);
    if (errno || *end || result > UINT32_MAX) return 1;
    *value = (uint32_t)result; return 0;
}

int main(int argc, char **argv) {
    int read_mode = argc == 5 && !strcmp(argv[1], "read");
    int snapshot_mode = argc == 4 && !strcmp(argv[1], "snapshot");
    int check_mode = argc == 2 && !strcmp(argv[1], "check");
    int inventory = argc == 2 && !strcmp(argv[1], "inventory");
    uint32_t address = 0, length = 0;
    const char *output_path = read_mode ? argv[4] : snapshot_mode ? argv[3] : NULL;
    if (snapshot_mode) {
        for (size_t i = 0; i < sizeof(snapshots)/sizeof(snapshots[0]); ++i)
            if (!strcmp(argv[2], snapshots[i].name)) {
                address = snapshots[i].address;
                length = snapshots[i].length;
            }
    }
    if ((!read_mode && !snapshot_mode && !check_mode && !inventory) ||
        (snapshot_mode && !length) || (read_mode &&
        (parse_number(argv[2], &address) || parse_number(argv[3], &length) || !length ||
         length % REPORT_SIZE || address % REPORT_SIZE || address >= FLASH_LIMIT ||
         length > FLASH_LIMIT - address))) {
        fprintf(stderr, "Usage: %s inventory | check | read ADDRESS MULTIPLE_OF_64 OUTPUT_FILE | snapshot NAME OUTPUT_FILE\n"
                "Snapshot names: device-id, nvm-status, user-row, calibration, port-a\n", argv[0]);
        return 2;
    }
    int vid = 0x0483, pid = 0x575a;
    CFNumberRef v = CFNumberCreate(NULL, kCFNumberIntType, &vid);
    CFNumberRef p = CFNumberCreate(NULL, kCFNumberIntType, &pid);
    const void *keys[] = {CFSTR(kIOHIDVendorIDKey), CFSTR(kIOHIDProductIDKey)};
    const void *values[] = {v, p};
    CFDictionaryRef match = CFDictionaryCreate(NULL, keys, values, 2,
                                              &kCFTypeDictionaryKeyCallBacks, &kCFTypeDictionaryValueCallBacks);
    IOHIDManagerRef manager = IOHIDManagerCreate(NULL, kIOHIDOptionsTypeNone);
    IOHIDManagerSetDeviceMatching(manager, match);
    CFRelease(match); CFRelease(v); CFRelease(p);
    IOReturn result = IOHIDManagerOpen(manager, kIOHIDOptionsTypeNone);
    if (result) { fprintf(stderr, "ManagerOpen failed: 0x%x\n", result); return 3; }
    CFSetRef devices = IOHIDManagerCopyDevices(manager);
    CFIndex count = devices ? CFSetGetCount(devices) : 0;
    printf("{\"event\":\"inventory\",\"matching_count\":%ld}\n", count);
    if (count < 1 || count > 16 || (!inventory && count != 1)) {
        fprintf(stderr, "Require one unambiguous target for requests.\n"); return 3;
    }
    IOHIDDeviceRef list[16]; CFSetGetValues(devices, (const void **)list);
    for (CFIndex i = 0; i < count; ++i) describe(list[i]);
    int status = 0;
    if (!inventory) {
        IOHIDDeviceRef device = list[0];
        CFTypeRef product = IOHIDDeviceGetProperty(device, CFSTR(kIOHIDProductKey));
        if (!product || CFGetTypeID(product) != CFStringGetTypeID() ||
            !CFEqual(product, CFSTR("LM-EA9")) ||
            number(device, CFSTR(kIOHIDMaxInputReportSizeKey)) != REPORT_SIZE ||
            number(device, CFSTR(kIOHIDMaxOutputReportSizeKey)) != REPORT_SIZE) {
            fprintf(stderr, "Product/report-size mismatch; no requests sent.\n"); return 3;
        }
        result = IOHIDDeviceOpen(device, kIOHIDOptionsTypeNone);
        if (result) { fprintf(stderr, "DeviceOpen failed: 0x%x\n", result); return 3; }
        IOHIDDeviceRegisterInputReportCallback(device, input_buffer, sizeof(input_buffer), input, NULL);
        IOHIDDeviceScheduleWithRunLoop(device, CFRunLoopGetCurrent(), kCFRunLoopDefaultMode);
        status = request(device, 0, 0);
        if (!status) printf("{\"event\":\"version\",\"value\":\"%u.%u.%u\"}\n", reply[6], reply[7], reply[8]);
        /* Upload-state ACKs echo our CHECK's zero padding, unlike the known
         * idle loader's 1.8.0 reply. This guard supplements the idle/no-updater
         * prerequisite; it cannot prevent the first CHECK being consumed by an
         * already armed upload. Requalify another firmware/loader separately.
         */
        if (!status && (read_mode || snapshot_mode) &&
            (reply[6] != 1 || reply[7] != 8 || reply[8] != 0)) {
            fprintf(stderr, "Memory reads are qualified only for the inspected stock 1.8.0 unit.\n");
            status = 1;
        }
        if (!status && (read_mode || snapshot_mode)) {
            printf("{\"event\":\"range\",\"address\":%u,\"length\":%u,\"snapshot\":", address, length);
            if (snapshot_mode) printf("\"%s\"", argv[2]); else printf("null");
            printf("}\n");
            /* Publish a file only after every block succeeds. Partial bytes stay in RAM. */
            uint8_t *bytes = malloc(length);
            if (!bytes) status = 1;
            for (uint32_t pos = 0; !status && pos < length; pos += REPORT_SIZE) {
                status = request(device, 1, address + pos);
                if (!status) memcpy(bytes + pos, reply, REPORT_SIZE);
            }
            if (!status) {
                FILE *file = fopen(output_path, "wbx");
                if (!file) { perror("output"); status = 1; }
                else {
                    if (fwrite(bytes, 1, length, file) != length) status = 1;
                    if (fclose(file)) status = 1;
                    if (status) remove(output_path);
                }
            }
            free(bytes);
        }
        IOHIDDeviceUnscheduleFromRunLoop(device, CFRunLoopGetCurrent(), kCFRunLoopDefaultMode);
        IOHIDDeviceClose(device, kIOHIDOptionsTypeNone);
    }
    CFRelease(devices); IOHIDManagerClose(manager, kIOHIDOptionsTypeNone); CFRelease(manager);
    return status;
}
