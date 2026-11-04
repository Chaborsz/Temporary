param(
    [string]$InputFile,
    [string]$OutputFile,
    [switch]$SelfTest
)
$ErrorActionPreference = 'Stop'

# Windows PowerShell 5.1 + .NET Framework: no Python, no downloads.
# Streaming weakfish-CBC implementation based on:
# blluv/pgmm_decrypt (MIT License, Copyright 2022 blluv).
# Source: https://github.com/blluv/pgmm_decrypt

$source = @'
using System;
using System.IO;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text;

public static class FobsWeakfishZip
{
    // Decryption output mapping: 16-byte Weakfish block cipher, AGTK version.
    static readonly int[] Map = { 11, 8, 9, 10, 13, 14, 15, 12, 3, 0, 1, 2, 5, 6, 7, 4 };
    static readonly byte[] IV = {
        0xA0,0x47,0xE9,0x3D,0x23,0x0A,0x4C,0x62,
        0xA7,0x44,0xB1,0xA4,0xEE,0x85,0x7F,0xBA
    };
    static string Hex(byte[] b)
    {
        return BitConverter.ToString(b).Replace("-","").ToLowerInvariant();
    }
    static bool JsonPrefix(byte[] b, int length)
    {
        int i = 0;
        if (length >= 3 && b[0] == 0xEF && b[1] == 0xBB && b[2] == 0xBF)
            i = 3;
        for (; i < length; i++)
        {
            if (b[i] == 0x20 || b[i] == 0x0A || b[i] == 0x0D || b[i] == 0x09)
                continue;
            return b[i] == (byte)'{' || b[i] == (byte)'[';
        }
        return false;
    }
    static string CheckZip(string path, long expected)
    {
        using (ZipArchive z = ZipFile.OpenRead(path))
        {
            if (z.Entries.Count != 1 ||
                z.Entries[0].FullName != "project_decrypted.json" ||
                z.Entries[0].Length != expected)
                throw new InvalidDataException("ZIP: nombre o longitud incorrecta.");
            using (Stream entry = z.Entries[0].Open())
            using (SHA256 hash = SHA256.Create())
            {
                byte[] buf = new byte[1024*1024];
                long total = 0;
                while (true)
                {
                    int n = entry.Read(buf, 0, buf.Length);
                    if (n == 0) break;
                    hash.TransformBlock(buf, 0, n, buf, 0);
                    total += n;
                }
                hash.TransformFinalBlock(new byte[0], 0, 0);
                if (total != expected)
                    throw new InvalidDataException("ZIP: lectura incompleta.");
                return Hex(hash.Hash);
            }
        }
    }
    public static string ConvertFile(string input, string output)
    {
        input = Path.GetFullPath(input);
        output = Path.GetFullPath(output);
        if (!File.Exists(input)) throw new FileNotFoundException("Falta project.json", input);
        if (String.Equals(input,output,StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("La salida no puede sustituir al original.");
        if (File.Exists(output))
            throw new IOException("El archivo de salida ya existe: " + output);
        string dir = Path.GetDirectoryName(output);
        if (!Directory.Exists(dir)) Directory.CreateDirectory(dir);
        string temp = Path.Combine(dir,"." + Path.GetFileName(output) +
                                    "." + Guid.NewGuid().ToString("N") + ".partial");
        long expected;
        string originalHash = "";
        try
        {
            using (FileStream f = new FileStream(input, FileMode.Open,
                FileAccess.Read,FileShare.Read,1024*1024,FileOptions.SequentialScan))
            {
                if (f.Length < 20 || ((f.Length-4) % 16) != 0)
                    throw new InvalidDataException("Longitud cifrada invalida.");
                byte[] header = new byte[4];
                if (f.Read(header,0,4)!=4 ||
                    header[0]!=(byte)'e' || header[1]!=(byte)'n' ||
                    header[2]!=(byte)'c')
                    throw new InvalidDataException("Cabecera 'enc' ausente.");
                if (header[3]>15)
                    throw new InvalidDataException("Padding fuera de rango.");
                expected=f.Length-4-header[3];
                if (expected<2) throw new InvalidDataException("JSON demasiado corto.");

                using (FileStream zipFile = new FileStream(temp,FileMode.CreateNew,
                    FileAccess.Write,FileShare.None,1024*1024))
                using (ZipArchive archive = new ZipArchive(zipFile,ZipArchiveMode.Create,false))
                using (SHA256 sha = SHA256.Create())
                {
                    ZipArchiveEntry entry = archive.CreateEntry(
                        "project_decrypted.json", CompressionLevel.Optimal);
                    using (Stream target = entry.Open())
                    {
                        byte[] cipher = new byte[1024*1024];
                        byte[] plain = new byte[cipher.Length];
                        byte[] prev = (byte[]) IV.Clone();
                        long remainingCipher=f.Length-4;
                        long remainingPlain=expected;
                        bool first = true;
                        while (remainingCipher>0)
                        {
                            int want=(int)Math.Min((long)cipher.Length,remainingCipher);
                            int count=0;
                            while (count<want)
                            {
                                int n=f.Read(cipher,count,want-count);
                                if (n==0)
                                    throw new EndOfStreamException("Cifrado truncado.");
                                count+=n;
                            }
                            for (int pos=0;pos<count;pos+=16)
                            {
                                for (int j=0;j<16;j++)
                                    plain[pos+j]=(byte)(cipher[pos+Map[j]] ^ prev[j]);
                                for (int j=0;j<16;j++)
                                    prev[j]=cipher[pos+j];
                            }
                            int use=(int)Math.Min((long)count,remainingPlain);
                            if (first)
                            {
                                if (!JsonPrefix(plain,Math.Min(use,4096)))
                                    throw new InvalidDataException(
                                        "El contenido descifrado no comienza como JSON.");
                                first=false;
                            }
                            target.Write(plain,0,use);
                            sha.TransformBlock(plain,0,use,plain,0);
                            remainingPlain-=use;
                            remainingCipher-=count;
                        }
                        if (remainingPlain!=0)
                            throw new InvalidDataException("Longitud descifrada incorrecta.");
                    }
                    sha.TransformFinalBlock(new byte[0],0,0);
                    originalHash=Hex(sha.Hash);
                }
            }
            string recoveredHash=CheckZip(temp,expected);
            if (!String.Equals(recoveredHash,originalHash,StringComparison.Ordinal))
                throw new InvalidDataException("Error de integridad: SHA-256 del ZIP.");
            File.Move(temp,output);
            return "ZIP_OK\nJSON_bytes=" + expected +
                   "\nJSON_SHA256=" + originalHash +
                   "\nZIP=" + output;
        }
        finally
        {
            if (File.Exists(temp))
                File.Delete(temp);
        }
    }
    public static string SelfTest()
    {
        string folder=Path.Combine(Path.GetTempPath(),
            "fobs-weakfish-test-"+Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(folder);
        try
        {
            // >1MiB tests the buffer boundary and nonzero padding.
            string header="{\"name\":\"Endurance\",\"id\":27,\"type\":\"arousal\"}";
            byte[] prefix=Encoding.UTF8.GetBytes(header);
            byte[] data=new byte[1024*1024+14];
            Buffer.BlockCopy(prefix,0,data,0,prefix.Length);
            for(int i=prefix.Length;i<data.Length;i++) data[i]=(byte)' ';
            int pad=(16-(data.Length%16))%16;
            byte[] padded=new byte[data.Length+pad];
            Buffer.BlockCopy(data,0,padded,0,data.Length);
            byte[] prev=(byte[])IV.Clone();
            byte[] ciphertext=new byte[padded.Length];
            for(int i=0;i<padded.Length;i+=16)
            {
                for (int j=0;j<16;j++)
                    ciphertext[i+Map[j]]=(byte)(padded[i+j]^prev[j]);
                Buffer.BlockCopy(ciphertext,i,prev,0,16);
            }
            string encrypted=Path.Combine(folder,"project.json");
            using(FileStream f=new FileStream(encrypted,FileMode.CreateNew))
            {
                f.Write(new byte[]{(byte)'e',(byte)'n',(byte)'c',(byte)pad},0,4);
                f.Write(ciphertext,0,ciphertext.Length);
            }
            string zip=Path.Combine(folder,"project_data.zip");
            string result=ConvertFile(encrypted,zip);
            string truth;
            using(SHA256 sha=SHA256.Create()) truth=Hex(sha.ComputeHash(data));
            if (result.IndexOf(truth,StringComparison.Ordinal)<0)
                throw new Exception("Selftest hash mismatch.");
            if (File.ReadAllBytes(encrypted).Length!=padded.Length+4)
                throw new Exception("Selftest input changed.");
            return "WEAKFISH_ZIP_SELFTEST_PASS; " + result;
        }
        finally { Directory.Delete(folder,true); }
    }
}
'@

try {
    Add-Type -TypeDefinition $source -ReferencedAssemblies @('System.IO.Compression.dll','System.IO.Compression.FileSystem.dll') -ErrorAction Stop
    if ($SelfTest) {
        Write-Output ([FobsWeakfishZip]::SelfTest())
        exit 0
    }
    if ([string]::IsNullOrWhiteSpace($InputFile)) {
        throw 'Debes arrastrar project.json al .bat.'
    }
    if ([string]::IsNullOrWhiteSpace($OutputFile)) {
        $OutputFile = Join-Path (Split-Path -Parent $InputFile) 'project_data.zip'
    }
    Write-Output ([FobsWeakfishZip]::ConvertFile($InputFile,$OutputFile))
    exit 0
}
catch {
    Write-Error ("DESCIFRADO_FALLIDO: " + $_.Exception.Message)
    exit 1
}
