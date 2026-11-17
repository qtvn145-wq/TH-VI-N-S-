"""PDF processing in a short-lived process; callers apply a time limit."""
import io
import json
import sys
import pypdfium2 as pdfium

def main():
    # Bound native allocations on Linux as well as output dimensions.
    try:
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (768*1024*1024,768*1024*1024))
        resource.setrlimit(resource.RLIMIT_CPU, (15,15))
    except (ImportError,ValueError,OSError):
        pass
    mode,path=sys.argv[1:3]
    with pdfium.PdfDocument(path) as doc:
        count=len(doc)
        if not 1<=count<=500: raise ValueError('PAGE_LIMIT')
        if mode=='info':
            for i in range(count):
                page=doc[i]
                width,height=page.get_size()
                page.close()
                if not (1<=width<=14400 and 1<=height<=14400): raise ValueError('PAGE_SIZE')
            print(json.dumps({'page_count':count}))
        elif mode=='render':
            number=int(sys.argv[3])
            if not 1<=number<=count: raise ValueError('PAGE_RANGE')
            page=doc[number-1]
            width,height=page.get_size()
            if min(width,height)<=0: raise ValueError('PAGE_SIZE')
            bitmap=page.render(scale=min(1600/width,2000/height,2.5))
            image=bitmap.to_pil().convert('RGB')
            output=io.BytesIO(); image.save(output,'JPEG',quality=88)
            image.close(); bitmap.close(); page.close()
            sys.stdout.buffer.write(output.getvalue())
        else: raise ValueError('MODE')

if __name__=='__main__':
    try: main()
    except Exception:
        sys.exit(2)
