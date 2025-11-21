
#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif
int printf(const char *format, ...);
char *strstr(const char *haystack, const char *needle);
long long cd_strlen(const char *str) {
    long long len = 0;
    while (str[len]) len++;
    return len;
}
long long find_substring(const char *str, const char *pattern) {
    if (!str || !pattern) return -1;
    char *found = strstr(str, pattern);
    return found ? (long long)(found - str) : -1;
}
