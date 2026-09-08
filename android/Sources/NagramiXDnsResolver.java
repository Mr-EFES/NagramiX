package com.mr_efes.nagramix;

import android.content.Context;

import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.ArrayList;

/** RFC 8484 resolver used only when a NagramiX DoH provider is selected. */
public final class NagramiXDnsResolver {
    private static final SecureRandom RANDOM = new SecureRandom();

    private NagramiXDnsResolver() {}

    public static boolean usesSystemResolver(Context context) {
        return "system".equals(NagramiXSettings.INSTANCE.preferences(context)
                .getString(NagramiXSettings.DNS_PROVIDER, "system"));
    }

    public static ArrayList<String> resolve(Context context, String hostname) {
        String endpoint = endpoint(context);
        if (endpoint == null || !isValidEndpoint(endpoint)) return null;
        ArrayList<String> result = query(endpoint, hostname, 1);
        if (result == null || result.isEmpty()) result = query(endpoint, hostname, 28);
        return result == null || result.isEmpty() ? null : result;
    }

    public static ArrayList<String> resolveSystem(String hostname) {
        try {
            ArrayList<String> result = new ArrayList<>();
            for (java.net.InetAddress address : java.net.InetAddress.getAllByName(hostname)) {
                String value = address.getHostAddress();
                if (value != null && !result.contains(value)) result.add(value);
            }
            return result.isEmpty() ? null : result;
        } catch (Exception ignore) {
            return null;
        }
    }

    public static boolean testEndpoint(String endpoint) {
        return isValidEndpoint(endpoint) && resolveAt(endpoint, "example.com") != null;
    }

    public static boolean isValidEndpoint(String value) {
        try {
            URL url = new URL(value);
            return "https".equalsIgnoreCase(url.getProtocol())
                    && url.getHost() != null && !url.getHost().isEmpty()
                    && value.indexOf(' ') < 0;
        } catch (Exception ignore) {
            return false;
        }
    }

    private static ArrayList<String> resolveAt(String endpoint, String hostname) {
        ArrayList<String> result = query(endpoint, hostname, 1);
        if (result == null || result.isEmpty()) result = query(endpoint, hostname, 28);
        return result == null || result.isEmpty() ? null : result;
    }

    private static String endpoint(Context context) {
        String provider = NagramiXSettings.INSTANCE.preferences(context)
                .getString(NagramiXSettings.DNS_PROVIDER, "system");
        if ("google".equals(provider)) return "https://dns.google/dns-query";
        if ("quad9".equals(provider)) return "https://dns.quad9.net/dns-query";
        if ("adguard".equals(provider)) return "https://dns.adguard-dns.com/dns-query";
        if ("mullvad".equals(provider)) return "https://dns.mullvad.net/dns-query";
        if ("cloudflare".equals(provider)) return "https://cloudflare-dns.com/dns-query";
        if ("custom".equals(provider)) return NagramiXSettings.INSTANCE.preferences(context)
                .getString(NagramiXSettings.CUSTOM_DOH_URL, "");
        return null;
    }

    private static ArrayList<String> query(String endpoint, String hostname, int type) {
        HttpURLConnection connection = null;
        try {
            int identifier = RANDOM.nextInt(0x10000);
            byte[] request = makeQuery(hostname, type, identifier);
            connection = (HttpURLConnection) new URL(endpoint).openConnection();
            connection.setRequestMethod("POST");
            connection.setDoOutput(true);
            connection.setConnectTimeout(8000);
            connection.setReadTimeout(12000);
            connection.setUseCaches(false);
            connection.setInstanceFollowRedirects(false);
            connection.setRequestProperty("Content-Type", "application/dns-message");
            connection.setRequestProperty("Accept", "application/dns-message");
            connection.setFixedLengthStreamingMode(request.length);
            try (java.io.OutputStream output = connection.getOutputStream()) {
                output.write(request);
            }
            if (connection.getResponseCode() != 200) return null;
            ByteArrayOutputStream response = new ByteArrayOutputStream();
            byte[] buffer = new byte[4096];
            int count;
            try (DataInputStream input = new DataInputStream(connection.getInputStream())) {
                while ((count = input.read(buffer)) >= 0) {
                    if (response.size() + count > 65535) return null;
                    response.write(buffer, 0, count);
                }
            }
            return parseResponse(response.toByteArray(), identifier, type);
        } catch (Exception ignore) {
            return null;
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private static byte[] makeQuery(String hostname, int type, int identifier) throws Exception {
        String normalized = hostname.replaceAll("\\.+$", "");
        if (normalized.isEmpty()) throw new IllegalArgumentException("Empty hostname");
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        DataOutputStream output = new DataOutputStream(bytes);
        output.writeShort(identifier);
        output.writeShort(0x0100);
        output.writeShort(1);
        output.writeShort(0);
        output.writeShort(0);
        output.writeShort(0);
        for (String label : normalized.split("\\.")) {
            byte[] encoded = label.getBytes(StandardCharsets.UTF_8);
            if (encoded.length == 0 || encoded.length > 63) throw new IllegalArgumentException("Invalid hostname");
            output.writeByte(encoded.length);
            output.write(encoded);
        }
        output.writeByte(0);
        output.writeShort(type);
        output.writeShort(1);
        return bytes.toByteArray();
    }

    private static ArrayList<String> parseResponse(byte[] data, int identifier, int expectedType) throws Exception {
        if (data.length < 12 || read16(data, 0) != identifier || (read16(data, 2) & 0x800f) != 0x8000) return null;
        int questions = read16(data, 4);
        int answers = read16(data, 6);
        int offset = 12;
        for (int i = 0; i < questions; i++) {
            offset = skipName(data, offset);
            if (offset + 4 > data.length) return null;
            offset += 4;
        }
        ArrayList<String> result = new ArrayList<>();
        for (int i = 0; i < answers; i++) {
            offset = skipName(data, offset);
            if (offset + 10 > data.length) return null;
            int type = read16(data, offset);
            int dnsClass = read16(data, offset + 2);
            int length = read16(data, offset + 8);
            offset += 10;
            if (offset + length > data.length) return null;
            if (dnsClass == 1 && type == expectedType && ((type == 1 && length == 4) || (type == 28 && length == 16))) {
                result.add(java.net.InetAddress.getByAddress(java.util.Arrays.copyOfRange(data, offset, offset + length)).getHostAddress());
            }
            offset += length;
        }
        return result;
    }

    private static int skipName(byte[] data, int offset) throws Exception {
        for (int labels = 0; labels < 128 && offset < data.length; labels++) {
            int length = data[offset++] & 0xff;
            if (length == 0) return offset;
            if ((length & 0xc0) == 0xc0) {
                if (offset >= data.length) break;
                return offset + 1;
            }
            if ((length & 0xc0) != 0 || length > 63 || offset + length > data.length) break;
            offset += length;
        }
        throw new IllegalArgumentException("Invalid DNS name");
    }

    private static int read16(byte[] data, int offset) {
        return ((data[offset] & 0xff) << 8) | (data[offset + 1] & 0xff);
    }
}
