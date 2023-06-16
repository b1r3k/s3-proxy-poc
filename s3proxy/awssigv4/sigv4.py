import hmac
import urllib.parse
from datetime import datetime
from hashlib import sha256


def format_amz_date():
    now = datetime.utcnow()
    return now.strftime("%Y%m%dT%H%M%SZ")


def normalize_url_path(path):
    if not path:
        return "/"
    return remove_dot_segments(path)


def remove_dot_segments(url):
    # RFC 3986, section 5.2.4 "Remove Dot Segments"
    # Also, AWS services require consecutive slashes to be removed,
    # so that's done here as well
    if not url:
        return ""
    input_url = url.split("/")
    output_list = []
    for x in input_url:
        if x and x != ".":
            if x == "..":
                if output_list:
                    output_list.pop()
            else:
                output_list.append(x)

    if url[0] == "/":
        first = "/"
    else:
        first = ""
    if url[-1] == "/" and output_list:
        last = "/"
    else:
        last = ""
    return first + "/".join(output_list) + last


def get_canonical_req(method, path, host, headers, params, body=b"", body_hash=None):
    cr = [method]
    if len(path) == 0:
        path = "/"
    if path[0] != "/":
        path = "/" + path
    normalized_path = urllib.parse.quote(normalize_url_path(path), safe="/~")
    cr.append(normalized_path)  # canonical uri
    qs_params = []
    for name, value in params.items():
        qname = urllib.parse.quote(str(name), safe="~")
        qvalue = urllib.parse.quote(str(value), safe="~") if value is not None else None
        if qvalue is not None:
            qs_params.append("%s=%s" % (qname, qvalue))
        else:
            qs_params.append("%s=" % qname)
    cr.append("&".join(sorted(qs_params)))

    # headers to sign
    headers_to_sign = []
    for name in set(map(lambda key: key.lower(), headers)):
        value = headers.get(name)
        headers_to_sign.append((name.lower(), value.strip() if value is not None else ""))

    headers_to_sign = list(sorted(headers_to_sign))

    cr.append("\n".join(n + ":" + v for n, v in headers_to_sign) + "\n")
    headers_to_sign = ";".join(n for n, v in headers_to_sign)
    cr.append(headers_to_sign)
    if body_hash is not None:
        cr.append(body_hash)
    else:
        cr.append(sha256(body).hexdigest())
    cr = "\n".join(cr)
    return cr, headers_to_sign


def get_string_to_sign(canonical_req, amz_date, region, service):
    date = amz_date[:8]
    sts = ["AWS4-HMAC-SHA256"]
    sts.append(amz_date)
    sts.append("/".join([date, region, service, "aws4_request"]))  # credential scope
    sts.append(sha256(canonical_req.encode("utf-8")).hexdigest())
    sts = "\n".join(sts)
    return sts


def sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), sha256).digest()


def get_signature(sts, secret, region, service, date):
    k_date = sign(("AWS4" + secret).encode("utf-8"), date[:8])
    k_region = sign(k_date, region)
    k_service = sign(k_region, service)
    k_signing = sign(k_service, "aws4_request")

    signature = hmac.new(k_signing, sts.encode("utf8"), sha256).hexdigest()
    return signature


def get_v4_signature(key, secret, host, region, service, method, path, headers, params=None, body=b"", body_hash=None):
    if params is None:
        params = {}
    if headers.get("x-amz-content-sha256") == "UNSIGNED-PAYLOAD":
        body_hash = "UNSIGNED-PAYLOAD"
    method = method.upper()
    amz_date = headers.setdefault("x-amz-date", format_amz_date())
    date = amz_date[:8]
    cr, headers_to_sign = get_canonical_req(method, path, host, headers, params, body, body_hash)
    # string to sign
    sts = get_string_to_sign(cr, amz_date, region, service)
    # signature
    signature = get_signature(sts, secret, region, service, amz_date)
    # auth header
    result = ["AWS4-HMAC-SHA256 Credential=" + "/".join((key, date, region, service, "aws4_request"))]
    result.append("SignedHeaders=" + headers_to_sign)
    result.append("Signature=" + signature)
    return ", ".join(result)
