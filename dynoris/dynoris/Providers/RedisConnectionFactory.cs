using Microsoft.Extensions.Configuration;
using StackExchange.Redis;
using System;

namespace dynoris.Providers
{
    public interface IRedisConnectionFactory
    {
        ConnectionMultiplexer Connection();
    }

    public class RedisConnectionFactory : IRedisConnectionFactory
    {
        /// <summary>
        ///     The _connection.
        /// </summary>
        private readonly Lazy<ConnectionMultiplexer> _connection;

        private readonly string _redisConnectionString;

        public RedisConnectionFactory(IConfiguration config)
        {
            _redisConnectionString = config.GetConnectionString("Redis");
            _connection = new Lazy<ConnectionMultiplexer>(() => ConnectionMultiplexer.Connect(_redisConnectionString));
        }

        public ConnectionMultiplexer Connection()
        {
            return _connection.Value;
        }
    }

}